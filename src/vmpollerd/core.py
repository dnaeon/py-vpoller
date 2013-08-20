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

"""

import os
import glob
import syslog

import zmq
from vmconnector.core import VMConnector
from vmpollerd.daemon import Daemon
from pysphere import MORTypes

class VMPollerException(Exception):
    """
    Generic VMPoller exception.

    """
    pass

class VMPollerDaemon(Daemon):
    """
    VMPollerDaemon class

    Prepares all VMPoller Agents to be ready for polling from the vCenters.

    Creates two sockets, one connected to the ZeroMQ proxy to receive client requests,
    the second socket is bound to tcp://localhost:11560 and is used for management.
    
    Extends:
        Daemon class

    Overrides:
        run() method

    """
    def run(self, config_dir="/etc/vm-poller"):
        """
        The main daemon loop.

        The 'config_dir' argument should point to a directory containing all *.conf files
        for the different vCenters we are connecting our VMPollerAgents to.
        
        Args:
            config_dir (str): A directory containing configuration files for the Agents
        
        Raises:
            VMPollerException

        """
        # Get the configuration files for our vCenters
        confFiles = self.get_configs(config_dir)
 
        # Our Agents and ZeroMQ context
        self.agents = dict()
        self.zcontext = zmq.Context()

        # Load the config for every Agent and vCenter
        for eachConf in confFiles:
            agent = VMPollerAgent(eachConf, ignore_locks=True, lockdir="/var/run/vm-pollerd", keep_alive=True)
            self.agents[agent.vcenter] = agent

        # Time to fire up our poller Agents
        self.start_agents()

        # Bind to our ZeroMQ proxy as a worker
        # TODO: The endpoint we bind should be configurable
        syslog.syslog("Connecting to the VMPoller Proxy server")
        self.worker = self.zcontext.socket(zmq.REP)

        try:
            self.worker.connect("tcp://localhost:11556")
        except zmq.ZMQError as e:
            raise VMPollerException, "Cannot connect worker to proxy: %s" % e

        # A management socket, used to control the VMPoller daemon
        self.mgmt = self.zcontext.socket(zmq.REP)

        try:
            self.mgmt.bind("tcp://127.0.0.1:11560")
        except zmq.ZMQError as e:
            raise VMPollerException, "Cannot bind management socket: %s" % e

        # Create a poll set for our two sockets
        self.zpoller = zmq.Poller()
        self.zpoller.register(self.worker, zmq.POLLIN)
        self.zpoller.register(self.mgmt, zmq.POLLIN)

        # Process messages from both sockets
        while True:
            socks = dict(self.zpoller.poll())

            # Process worker message
            if socks.get(self.worker) == zmq.POLLIN:
                msg = self.worker.recv_json()
                result = self.process_worker_message(msg)
                self.worker.send_json(result)

            if socks.get(self.mgmt) == zmq.POLLIN:
                msg = self.mgmt.recv_json()
                result = self.process_mgmt_message(msg)
                self.mgmt.send_json(result)

        # TODO: Proper shutdown and zmq context termination
        #       This should be done in the shutdown/stop command
        self.shutdown_agents()
        self.worker.close()
        self.mgmt.close()
        self.stop()

    def get_configs(self, config_dir):
        """
        Gets the configuration files for the vCenters
        
        The 'config_dir' argument should point to a directory containing all .conf files
        for the different vCenters we are connecting our VMPollerAgents to.
        
        Args:
            config_dir (str): A directory containing configuration files for the Agents

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
            raise VMPollerException, "No config files found in %s" % config_dir

        return confFiles

    def start_agents(self):
        """
        Connects all VMPoller Agents to their vCenters

        """
        for eachAgent in self.agents:
            try:
                self.agents[eachAgent].connect(timeout=3)
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

        The message is passed to the VMPollerAgent object of the respective vCenter in
        order to do the actual polling.

        The messages that we support are polling for datastores and hosts.

        Args:
            msg (dict): A dictionary containing the client request message

        Returns:
            A dict object which contains the requested property
            
        """
        
        # We require to have 'type' and 'vcenter' keys in our message
        if not all(k in msg for k in ("type", "vcenter")):
            return { "status": -1, "reason": "Missing message properties (e.g. type and/or vcenter)" }

        vcenter = msg["vcenter"]
        
        if msg["type"] == "datastores":
            return self.agents[vcenter].get_datastore_property(msg)
        elif msg["type"] == "hosts":
            return self.agents[vcenter].get_host_property(msg)
        else:
            return {"status": -1, "reason": "Unknown object type to poll requested" }

    def process_mgmt_message(self, msg):
        """
        Processes a message for the management interface

        """
        pass
        
class VMPollerAgent(VMConnector):
    """
    VMPollerAgent object.

    Defines methods for retrieving vSphere objects' properties.

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
            return { "status": -1, "reason": "Missing message properties (e.g. vcenter/host)" }
        
        # Search is done by using the 'name' property of the ESX Host
        # Properties we want to retrieve are 'name' and the requested property
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['name', msg['property']]

        # Check if we are connected first
        if not self.viserver.is_connected():
            self.reconnect()
        
        syslog.syslog('[%s] Retrieving %s for host %s' % (self.vcenter, msg['property'], msg['name']))

        # TODO: Custom zabbix properties and convertors
        # TODO: Exceptions, e.g. pysphere.resources.vi_exception.VIApiException:

        # Find the host's Managed Object Reference (MOR)
        mor = [x for x, host in self.viserver.get_hosts().items() if host == msg['name']]

        # Do we have a match?
        if not mor:
            return { "status": -1, "reason": "Unable to find the host" }
        else:
            mor = mor.pop()
            
        # Get the properties
        results = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                               from_node=mor,
                                                               obj_type=MORTypes.HostSystem).pop()

        # Get the property value
        val = [x.Val for x in results.PropSet if x.Name == msg['property']].pop()

        return { "status": 0, "host": msg['name'], "property": msg['property'], "value": val }
            
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
            return { "status": -1, "reason": "Missing message properties (e.g. vcenter/ds_url)" }
        
        # Search is done by using the 'info.name' and 'info.url' properties
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        # 
        property_names = ['info.name', 'info.url', msg['property']]

        # Check if we are connected first
        if not self.viserver.is_connected():
            self.reconnect()
        
        syslog.syslog('[%s] Retrieving %s for datastore %s' % (self.vcenter, msg['property'], msg['name']))

        # TODO: Custom zabbix properties and convertors
        # TODO: Exceptions, e.g. pysphere.resources.vi_exception.VIApiException:
        
        results = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                               obj_type=MORTypes.Datastore)
        
        # Iterate over the results and find our datastore with 'info.name' and 'info.url' properties
        for item in results:
            props = [(p.Name, p.Val) for p in item.PropSet]
            d = dict(props)

            # break if we have a match
            if d['info.name'] == msg['name'] and d['info.url'] == msg['ds_url']:
                break
        else:
            return { "status": -1, "reason": "Unable to find the datastore" }

        return { "status": 0, "datastore": msg["name"], "property": msg["property"], "value": d[msg["property"]] } 
    
class VMPollerProxy(Daemon):
    """
    VMPoller Proxy object.

    ZeroMQ proxy which load-balances all client requests to a
    pool of connected ZeroMQ workers.

    Extends:
        Daemon

    Overrides:
        run() method

    """
    def run(self):
        # ZeroMQ context
        self.zcontext = zmq.Context()

        # Socket facing clients
        # TODO: The endpoint we bind to should be configurable
        self.frontend = self.zcontext.socket(zmq.ROUTER)
        self.frontend.bind("tcp://*:11555")

        # Socket facing workers
        # TODO: The endpoint we bind should be configurable
        self.backend = self.zcontext.socket(zmq.DEALER)
        self.backend.bind("tcp://*:11556")

        # Start the proxy
        syslog.syslog("Starting the VMPoller Proxy")
        zmq.proxy(self.frontend, self.backend)

        # This is never reached...
        self.frontend.close()
        self.backend.close()
        self.zcontext.term()
