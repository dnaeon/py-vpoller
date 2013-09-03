# Copyright (c) 2013 Marin Atanasov Nikolov <dnaeon@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer
#    in this position and unchanged.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR(S) ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR(S) BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Core module for the VMware vSphere Poller

The principal work of the VMPoller can be seen in the diagram below.

The diagram shows clients sending ZeroMQ messages to a ZeroMQ proxy,
which load balances client requests between two threaded workers.

   		    +--------+   +--------+   +--------+
    		    | Client |   | Client |   | Client |
                    +--------+   +--------+   +--------+
                    |  REQ   |   |  REQ   |   |  REQ   |
                    +--------+   +--------+   +--------+
                        |             |            |
                        +-------------+------------+
                                      |
                                      | -> TCP socket
                                      |
                                  +----------+
                                  |  ROUTER  |
                                  +----------+
                                  |   Proxy  | -> Load Balancer (ZeroMQ Broker)
                                  +----------+
                                  |  DEALER  |
                                  +----------+
                                       |
                                       |
                                       |
                   +---------------------------------------+     
                   |                                       |
              +--------+                              +--------+
              | ROUTER |		     	      | ROUTER |
              +--------+			      +--------+
              | Worker |			      | Worker |
              +--------+			      +--------+
              | DEALER |			      | DEALER |
              +--------+			      +--------+
                   |				         |
                   | -> INPROC socket	                 | -> INPROC socket
                   |			                 |
       +-----------+----------+		     +-----------+-----------+
       |           |          |		     |           |           |
  +--------+  +--------+  +--------+	+--------+  +--------+  +--------+
  |   REP  |  |   REP  |  |   REP  |	|   REP  |  |   REP  |  |   REP  |
  +--------+  +--------+  +--------+	+--------+  +--------+  +--------+ 
  | Thread |  | Thread |  | Thread |	| Thread |  | Thread |  | Thread |
  +--------+  +--------+  +--------+	+--------+  +--------+  +--------+
      |           |           |             |           |           |
      +-----------+-----------+-------------+-----------+-----------+
                                       |
                                       |
                                       |
                     +---------------- +----------------+
                     |                 |                |
              +-------------+   +-------------+   +-------------+
              | vSphere API |   | vSphere API |   | vSphere API |
              +-------------+   +-------------+   +-------------+
              |   vCenter   |   |   vCenter   |   |   vCenter   |
              +-------------+   +-------------+   +-------------+
              |  ESX Hosts  |   |  ESX Hosts  |   |  ESX Hosts  |
              +-------------+   +-------------+   +-------------+
              |  Datastores |   |  Datastores |   |  Datastores |
              +-------------+   +-------------+   +-------------+
              
"""   

import os
import glob
import json
import time
import syslog
import threading
import ConfigParser

import zmq
from vmconnector.core import VMConnector
from vmpollerd.daemon import Daemon
from pysphere import MORTypes

class VMPollerException(Exception):
    """
    Generic VMPoller exception.

    """
    pass

class VMPollerWorker(Daemon):
    """
    VMPollerWorker class

    Prepares all vSphere Agents to be ready for polling from the vCenters.

    This is the main VMPoller worker, which contains all worker agents (vSphere Agents/Pollers)
    
    Creates two sockets, one connected to the ZeroMQ proxy to receive client requests,
    the second socket is used for management, e.g. querying status information, shutdown, etc.

    Extends:
        Daemon class

    Overrides:
        run() method

    """
    def run(self, config_file, start_agents=False):
        """
        The main worker method.

        Args:
            config_file (str):  Configuration file for the VMPollerWorker
            run_agents  (bool): If True then all vSphere Agents will be started up upfront
            			any polling has occurred. Otherwise, a vSphere Agent will be
                                started only if needed.
        
        Raises:
            VMPollerException

        """
        if not os.path.exists(config_file):
            raise VMPollerException, "Configuration file does not exists: %s" % config_file

        config = ConfigParser.ConfigParser()
        config.read(config_file)

        self.proxy_endpoint  = config.get('Default', 'broker')
        self.mgmt_endpoint   = config.get('Default', 'mgmt')
        self.vcenter_configs = config.get('Default', 'vcenters')
        self.threads_num     = int(config.get('Default', 'threads'))

        # A flag to signal that our threads and daemon should be terminated
        self.time_to_die = False

        # A list to hold our threads
        self.threads = []
        
        # Get the configuration files for our vCenters
        confFiles = self.get_vcenter_configs(self.vcenter_configs)
 
        # Our Worker's vSphere Agents and ZeroMQ context
        self.agents = dict()
        self.zcontext = zmq.Context()

        # Load the config for every vSphere Agent
        for eachConf in confFiles:
            agent = VSphereAgent(eachConf, ignore_locks=True, lockdir="/var/run/vmpoller", keep_alive=True)
            self.agents[agent.vcenter] = agent

        # Start the vSphere Agents only if requested to do so
        if start_agents:
            self.start_agents()

        # A management socket, used to control the VMPollerWorker daemon
        self.mgmt = self.zcontext.socket(zmq.REP)

        try:
            self.mgmt.bind(self.mgmt_endpoint)
        except zmq.ZMQError as e:
            raise VMPollerException, "Cannot bind management socket: %s" % e

        # Create a ROUTER socket for forwarding client requests to our worker threads
        syslog.syslog("Connecting to the VMPoller Proxy server")
        self.router = self.zcontext.socket(zmq.ROUTER)

        try:
            self.router.connect(self.proxy_endpoint)
        except zmq.ZMQError as e:
            raise VMPollerException, "Cannot connect worker to proxy: %s" % e

        # Create a DEALER socket for passing messages from our worker threads back to the clients
        self.dealer = self.zcontext.socket(zmq.DEALER)
        self.dealer.bind("inproc://workers")
        
        for i in xrange(self.threads_num):
            thread = threading.Thread(target=self.worker_thread, args=("inproc://workers", self.zcontext))
            self.threads.append(thread)
            thread.daemon = True
            thread.start()

        #zmq.proxy(self.router, self.dealer)
            
        # Create a poll set for our sockets
        self.zpoller = zmq.Poller()
        self.zpoller.register(self.router, zmq.POLLIN)
        self.zpoller.register(self.dealer, zmq.POLLIN)
        self.zpoller.register(self.mgmt, zmq.POLLIN)

        # Enter the daemon loop from here
        while not self.time_to_die:
            socks = dict(self.zpoller.poll())

            # ROUTER socket, forward messages to the backend
            if socks.get(self.router) == zmq.POLLIN:
                msg = self.router.recv()
                more = self.router.getsockopt(zmq.RCVMORE)
                if more:
                    self.dealer.send(msg, zmq.SNDMORE)
                else:
                    self.dealer.send(msg)

            # DEALER socket, forward messages back to the clients
            if socks.get(self.dealer) == zmq.POLLIN:
                msg = self.dealer.recv()
                more = self.dealer.getsockopt(zmq.RCVMORE)
                if more:
                    self.router.send(msg, zmq.SNDMORE)
                else:
                    self.router.send(msg)

            # Management socket
            if socks.get(self.mgmt) == zmq.POLLIN:
                msg = self.mgmt.recv_json()
                result = self.process_mgmt_message(msg)
                self.mgmt.send(result)

        # Shutdown time has arrived, let's clean up a bit
        for eachThread in self.threads:
            eachThread.join(1)

        self.shutdown_agents()
        self.router.close()
        self.dealer.close()
        self.mgmt.close()
 #       self.zcontext.term()
        self.stop()

    def worker_thread(self, endpoint, context):
        """
        Worker thread routine

        Passes messages to the vSphere Agents for polling.

        Each thread creates a socket to the dealer and communicates
        using inproc with the DEALER.

        """
        socket = context.socket(zmq.REP)
        socket.connect(endpoint)
        
        while not self.time_to_die:
            msg = socket.recv_json()
            result = self.process_worker_message(msg)
            socket.send(result)

        # Let's clean up a bit here
        socket.close()
            
    def get_vcenter_configs(self, config_dir):
        """
        Gets the configuration files for the vCenters
        
        The 'config_dir' argument should point to a directory containing all .conf files
        for the different vCenters we are connecting our VSphereAgents to.
        
        Args:
            config_dir (str): A directory containing configuration files for the vSphere Agents

        Returns:
            A list of all configuration files found in the config directory
        
        Raises:
            VMPollerException
            
        """
        if not os.path.exists(config_dir) or not os.path.isdir(config_dir):
            raise VMPollerException, "%s does not exists or is not a directory" % config_dir
        
        # Get all *.conf files for the different vCenters
        path = os.path.join(config_dir, "*.conf")
        confFiles = glob.glob(path)

        if not confFiles:
            raise VMPollerException, "No vCenter config files found in %s" % config_dir

        return confFiles

    def start_agents(self):
        """
        Connects all VMPoller Agents to their vCenters

        """
        for eachAgent in self.agents:
            try:
                self.agents[eachAgent].connect()
            except Exception as e:
                print 'Cannot connect to %s: %s' % (eachAgent, e)

    def shutdown_agents(self):
        """
        Disconnects all VMPoller Agents from their vCenters

        """
        for eachAgent in self.agents:
            self.agents[eachAgent].disconnect()

    def process_worker_message(self, msg):
        """
        Processes a client request message

        The message is passed to the VSphereAgent object of the respective vCenter in
        order to do the actual polling.

        The messages that we support are polling for datastores and hosts.

        Args:
            msg (dict): A dictionary containing the client request message

        Returns:
            A dict object which contains the requested property
            
        """
        
        # We require to have 'type', 'cmd' and 'vcenter' keys in our message
        if not all(k in msg for k in ("type", "cmd", "vcenter")):
            return "Missing message properties (e.g. type/cmd/vcenter)"

        vcenter = msg["vcenter"]

        if not self.agents.get(vcenter):
            return "Unknown vCenter Agent requested"
        
        if msg["type"] == "datastores" and msg["cmd"] == "poll":
            return self.agents[vcenter].get_datastore_property(msg)
        elif msg["type"] == "datastores" and msg["cmd"] == "discover":
            return self.agents[vcenter].discover_datastores()
        elif msg["type"] == "hosts" and msg["cmd"] == "poll":
            return self.agents[vcenter].get_host_property(msg)
        elif msg["type"] == "hosts" and msg["cmd"] == "discover":
            return self.agents[vcenter].discover_hosts()
        else:
            return "Unknown command received"

    def process_mgmt_message(self, msg):
        """
        Processes a message for the management interface

        """
        # Check if we have a command to process
        if not "cmd" in msg:
            return "Missing command name"

        if msg["cmd"] == "shutdown":
            self.time_to_die = True
            syslog.syslog("VMPoller Worker is shutting down")
            return "Shutting down VMPoller Worker"
        
class VSphereAgent(VMConnector):
    """
    VSphereAgent class

    Defines methods for retrieving vSphere objects' properties.

    These are the worker agents that do the actual polling from the vCenters.

    Extends:
        VMConnector

    """
    def get_host_property(self, msg):
        """
        Get property of an object of type HostSystem and return it.

        Example client message to get a host property could be:

        msg = { "type":     "hosts",
                "vcenter":  "sof-vc0-mnik",
                "name":     "sof-dev-d7-mnik",
                "property": "hardware.memorySize"
              }
        
        Args:
            msg (dict): The client message

        Returns:
            The requested property value

        """
        # Sanity check for required attributes in the message
        if not all(k in msg for k in ("type", "vcenter", "name", "property")):
            return "Missing message properties (e.g. vcenter/host)"

        # Check if we are connected first
        if not self.viserver.is_connected():
            self.reconnect()
        
        # Search is done by using the 'name' property of the ESX Host
        # Properties we want to retrieve are 'name' and the requested property
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['name', msg['property']]

        # Some of the properties we process need to be converted to a Zabbix-friendly value
        # before passing the value back to the Zabbix Agents
        zbx_helpers = {
            'summary.quickStats.overallCpuUsage':            lambda p: p * 1048576, # The value we return is in Hertz
            'summary.quickStats.overallMemoryUsage':         lambda p: p * 1048576, # The value we return is in Bytes
            'summary.quickStats.distributedMemoryFairness':  lambda p: p * 1048576, # The value we return is in Bytes
            'runtime.inMaintenanceMode':                     lambda p: int(p),      # The value we return is integer
            'summary.config.vmotionEnabled':                 lambda p: int(p),      # The value we return is integer
            'summary.rebootRequired':                        lambda p: int(p),      # The value we return is integer
            'runtime.bootTime':                              lambda p: time.strftime('%Y-%m-%d %H:%M:%S', p),
        }
            
        syslog.syslog('[%s] Retrieving %s for host %s' % (self.vcenter, msg['property'], msg['name']))

        # Find the host's Managed Object Reference (MOR)
        mor = [x for x, host in self.viserver.get_hosts().items() if host == msg['name']]

        # Do we have a match?
        if not mor:
            return "Unable to find the requested host"
        else:
            mor = mor.pop()
            
        # Get the properties
        try:
            results = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                                   from_node=mor,
                                                                   obj_type=MORTypes.HostSystem).pop()
        except Exception as e:
            return "Cannot get property for host %s: %s" % (msg["name"], e)

        # Do we have something to return?
        if not results:
            return "Did not find property %s for host %s" % (msg["property"], msg["name"])
        
        # Get the property value
        val = [x.Val for x in results.PropSet if x.Name == msg['property']].pop()

        # Do we need to convert this value to a Zabbix-friendly one?
        if msg["property"] in zbx_helpers:
            val = zbx_helpers[msg["property"]](val)

        return val
            
    def get_datastore_property(self, msg):
        """
        Get property of an object of type Datastore and return it.

        Example client message to get a host property could be:

        msg = { "type":     "datastores",
                "vcenter":  "sof-vc0-mnik",
                "name":     "datastore1",
                "ds_url":   "ds:///vmfs/volumes/5190e2a7-d2b7c58e-b1e2-90b11c29079d/",
                "property": "summary.capacity"
              }
        
        Args:
            msg (dict): The client message
        
        Returns:
            The requested property value

        """
        # Sanity check for required attributes in the message
        if not all(k in msg for k in ("type", "vcenter", "name", "ds_url", "property")):
            return "Missing message properties (e.g. vcenter/ds_url)"

        # Check if we are connected first
        if not self.viserver.is_connected():
            self.reconnect()
        
        # Search is done by using the 'info.name' and 'info.url' properties
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        # 
        property_names = ['info.name', 'info.url', msg['property']]

        # Custom properties, which are not available in the vSphere Web SDK
        # Keys are the property names and values are a list/tuple of the properties required to
        # calculate the custom properties
        custom_zbx_properties = {
            'ds_used_space_percentage': ('summary.freeSpace', 'summary.capacity')
        }
                    
        # Some of the properties we process need to be converted to a Zabbix-friendly value
        # before passing the value back to the Zabbix Agents
        zbx_helpers = {
            'ds_used_space_percentage': lambda d: round(100 - (float(d['summary.freeSpace']) / float(d['summary.capacity']) * 100), 2),
        }

        # Check if we have a custom property requested
        # If we have a custom property we need to append the required properties
        # and also remove the custom one, otherwise we will get an exception
        if msg["property"] in custom_zbx_properties:
            property_names.extend(custom_zbx_properties[msg["property"]])
            property_names.remove(msg["property"])

        syslog.syslog('[%s] Retrieving %s for datastore %s' % (self.vcenter, msg['property'], msg['name']))

        try:
            results = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                                   obj_type=MORTypes.Datastore)
        except Exception as e:
            return "Cannot get property for datastore %s: %s" % (msg["name"], e)
            
        # Iterate over the results and find our datastore with 'info.name' and 'info.url' properties
        for item in results:
            props = [(p.Name, p.Val) for p in item.PropSet]
            d = dict(props)

            # break if we have a match
            if d['info.name'] == msg['name'] and d['info.url'] == msg['ds_url']:
                break
        else:
            return "Unable to find datastore %s" % msg["name"]

        # Do we need to convert this value to a Zabbix-friendly one?
        if msg["property"] in zbx_helpers:
            val = zbx_helpers[msg["property"]](d)
        else:
            # No need to convert anything
            val = d[msg["property"]] if d.get(msg["property"]) else 0 # Make sure we've got the property

        return val

    def discover_hosts(self):
        """
        Discoveres all ESX hosts registered in the VMware vCenter server.

        Returns:
            The returned data is a JSON object, containing the discovered ESX hosts.

        """
        # Check if we are connected first
        if not self.viserver.is_connected():
            self.reconnect()
        
        #
        # Properties we want to retrieve are 'name' and 'runtime.powerState'
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['name', 'runtime.powerState']

        # Property <name>-<macros> mappings that Zabbix uses
        property_macros = { 'name': '{#ESX_NAME}', 'runtime.powerState': '{#ESX_POWERSTATE}' }
        
        syslog.syslog('[%s] Discovering ESX hosts' % self.vcenter)

        # Retrieve the data
        results = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                               obj_type=MORTypes.HostSystem)

        # Iterate over the results and prepare the JSON object
        json_data = []
        for item in results:
            props = [(property_macros[p.Name], p.Val) for p in item.PropSet]
            d = dict(props)
            
            # remember on which vCenter this ESX host runs on
            d['{#VCENTER_SERVER}'] = self.vcenter
            json_data.append(d)

        return json.dumps({ 'data': json_data}, indent=4)

    def discover_datastores(self):
        """
        Discovers all datastores registered in a VMware vCenter server.

        Returns:
            The returned data is a JSON object, containing the discovered datastores.

        """
        # Check if we are connected first
        if not self.viserver.is_connected():
            self.reconnect()
        
        #
        # Properties we want to retrieve about the datastores
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['info.name',
                          'info.url',
                          'summary.accessible',
                          ]

        # Property <name>-<macro> mappings that Zabbix uses
        property_macros = {'info.name':          '{#DS_NAME}',
                           'info.url':           '{#DS_URL}',
                           'summary.accessible': '{#DS_ACCESSIBLE}',
                           }
        
        syslog.syslog('[%s] Discovering datastores' % self.vcenter)
        
        # Retrieve the data
        results = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                                obj_type=MORTypes.Datastore)

        # Iterate over the results and prepare the JSON object
        json_data = []
        for item in results:
            props = [(property_macros[p.Name], p.Val) for p in item.PropSet]
            d = dict(props)

            # Convert the 'summary.accessible' property to int as Zabbix does not understand True/False
            d['{#DS_ACCESSIBLE}'] = int(d['{#DS_ACCESSIBLE}'])
            
            # Remember on which vCenter is this datastore
            d['{#VCENTER_SERVER}'] = self.vcenter

            json_data.append(d)

        return json.dumps({ 'data': json_data}, indent=4)
        
class VMPollerProxy(Daemon):
    """
    VMPoller Proxy class

    ZeroMQ proxy/broker which load-balances all client requests to a
    pool of connected ZeroMQ workers.

    Extends:
        Daemon

    Overrides:
        run() method

    """
    def run(self, config_file="/etc/vm-poller/vm-pollerd-proxy.conf"):
        if not os.path.exists(config_file):
            raise VMPollerException, "Cannot read configuration for proxy: %s" % config_file 

        config = ConfigParser.ConfigParser()
        config.read(config_file)

        self.frontend_endpoint = config.get('Default', 'frontend')
        self.backend_endpoint  = config.get('Default', 'backend')
        
        # ZeroMQ context
        self.zcontext = zmq.Context()

        # Socket facing clients
        self.frontend = self.zcontext.socket(zmq.ROUTER)

        try:
            self.frontend.bind(self.frontend_endpoint)
        except zmq.ZMQError as e:
            raise VMPollerException, "Cannot bind frontend socket: %s" % e

        # Socket facing workers
        self.backend = self.zcontext.socket(zmq.DEALER)

        try:
            self.backend.bind(self.backend_endpoint)
        except zmq.ZMQError as e:
            raise VMPollerException, "Cannot bind backend socket: %s" % e

        # Start the proxy
        syslog.syslog("Starting the VMPoller Proxy")
        zmq.proxy(self.frontend, self.backend)

        # This is never reached...
        self.frontend.close()
        self.backend.close()
        self.zcontext.term()

class VMPollerClient(object):
    """
    VMPoller Client class

    Defines methods for use by clients for sending out message requests.

    Sends out messages to a VMPoller Proxy server requesting properties of
    different vSphere objects, e.g. datastores, hosts, etc.

    Returns:
        The result message back.
        
    """
    def __init__(self, config_file="/etc/vm-poller/vm-pollerd-client.conf"):
        if not os.path.exists(config_file):
            raise VMPollerException, "Config file %s does not exists" % config_file

        config = ConfigParser.ConfigParser()
        config.read(config_file)

        self.timeout  = config.get('Default', 'timeout')
        self.retries  = int(config.get('Default', 'retries'))
        self.endpoint = config.get('Default', 'endpoint')
        
        self.zcontext = zmq.Context()
        
        self.zclient = self.zcontext.socket(zmq.REQ)
        self.zclient.connect(self.endpoint)
        self.zclient.setsockopt(zmq.LINGER, 0)

        self.zpoller = zmq.Poller()
        self.zpoller.register(self.zclient, zmq.POLLIN)

    def run(self, msg):
        # Partially based on the Lazy Pirate Pattern
        # http://zguide.zeromq.org/py:all#Client-Side-Reliability-Lazy-Pirate-Pattern

        result = None
        
        while self.retries > 0:
            # Send our message out
            self.zclient.send_json(msg)
            
            socks = dict(self.zpoller.poll(self.timeout))

            # Do we have a reply?
            if socks.get(self.zclient) == zmq.POLLIN:
                result = self.zclient.recv()
                break
            else:
                # We didn't get a reply back from the server, let's retry
                self.retries -= 1
                syslog.syslog("Did not receive reply from server, retrying...")
                
                # Socket is confused. Close and remove it.
                self.zclient.close()
                self.zpoller.unregister(self.zclient)

                # Re-establish the connection
                self.zclient = self.zcontext.socket(zmq.REQ)
                self.zclient.connect(self.endpoint)
                self.zclient.setsockopt(zmq.LINGER, 0)
                self.zpoller.register(self.zclient, zmq.POLLIN)

        # Close the socket and terminate the context
        self.zclient.close()
        self.zpoller.unregister(self.zclient)
        self.zcontext.term()

        # Did we have any result reply at all?
        if not result:
            syslog.syslog("Did not receive a reply from the server, aborting...")
            return "Did not receive reply from the server, aborting..."
        
        return result
