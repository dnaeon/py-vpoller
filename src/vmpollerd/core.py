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

class VMPollerDaemon(object):
    def __init__(self, config_dir):
        """
        VMPollerDaemon object

        Prepares all VMPoller Agents to be ready for polling from multiple vCenters.

        Args:
            config_dir (str): A directory containing configuration files for the Agents

        Raises:
            VMPollerException
        
        """
        if not os.path.exists(config_dir) or not os.path.isdir(config_dir):
            raise VMPollerException, "%s does not exists or is not a directory"

        self.agents = dict()
        self.zcontext = zmq.Context()
        path = os.path.join(config_dir, "*.conf")
        confFiles = glob.glob(path)
        
        for eachConf in confFiles:
            agent = VMPollerAgent(eachConf, ignore_locks=True, lockdir="/var/run/vm-poller", keep_alive=True)
            self.agents[agent.vcenter] = agent

    def run(self):
        self.start_agents()

        # TODO: This should be a poller instead of REQ/REP sockets
        print "Starting a REP socket on *:9999 ..."

        # TODO: This should be set as a attribute
        socket  = self.zcontext.socket(zmq.REP)
        socket.bind("tcp://*:9999")

        while True:
            msg = socket.recv_json()

            print "Received: %s" % msg
            result = self.process_request(msg)

            print "Sending: ", result
            socket.send_pyobj(result)

        # TODO: Proper shutdown and zmq context termination
        self.shutdown_agents()
            
    def start_agents(self):
        # TODO: Check for exceptions here
        for eachAgent in self.agents:
            try:
                self.agents[eachAgent].connect(timeout=3)
            except Exception as e:
                print 'Cannot connect to %s: %s' % (eachAgent, e)

    def shutdown_agents(self):
        for eachAgent in self.agents:
            self.agents[eachAgent].disconnect()

    def process_request(self, msg):
        commands = { "status": "no-command-here-yet",
                     "poll"  : self.process_poll_cmd
                   }

        if not 'cmd' in msg:
            return {'status': -1, 'reason': 'No command specified'}

        if not msg['cmd'] in commands:
            return {'status': -1, 'reason': 'Unknown command'}

        return commands[msg['cmd']](msg)

    def process_poll_cmd(self, msg):
        # TODO: sanity check of the received message
        if msg['type'] == 'datastores':
            return self.agents[msg['vcenter']].get_datastore_property(msg['name'], msg['ds_url'], msg['property'])
        elif msg['type'] == 'hosts':
            return self.agents[msg['vcenter']].get_host_property(msg['name'], msg['property'])
        else:
            return {'status': -1, 'reason': 'Unknown poll command'}
    
class VMPollerAgent(VMConnector):
    """
    VMPollerAgent object.

    Defines methods for retrieving vSphere objects' properties.

    Extends:
        VMConnector

    """
    def get_host_property(self, name, prop):
        """
        Get property of an object of type HostSystem and return it.

        Args:
            name    (str): Name of the host
            prop    (str): Name of the property as defined by the vSphere SDK API

        Returns:
            The requested property value

        """
        # Search is done by using the 'name' property
        # Properties we want to retrieve are 'name' and the requested property
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        # 
        property_names = ['name', prop]

        # Check if we are connected first
        if not self.viserver.is_connected():
            self.reconnect()
        
        syslog.syslog('[%s] Retrieving %s for host %s' % (self.vcenter, prop, name))

        # TODO: Custom zabbix properties and convertors
        # TODO: Exceptions, e.g. pysphere.resources.vi_exception.VIApiException:
        # TODO: See if you can optimize this and directly find the host instead of searching for it

        # Find the host's Managed Object Reference (MOR)
        mor = [x for x, host in self.viserver.get_hosts().items() if host == name]

        # Do we have a match?
        if not mor:
            return -1
        else:
            mor = mor.pop()
            
        # Get the properties
        results = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                               from_node=mor,
                                                               obj_type=MORTypes.HostSystem).pop()

        # Get the property value
        val = [x.Val for x in results.PropSet if x.Name == prop].pop()

        return { "status": 0, "host": name, "property": prop, "value": val }
            
    def get_datastore_property(self, name, url, prop):
        """
        Get property of an object of type Datastore and return it.

        Args:
            name    (str): Name of the datatstore object
            url     (str): Datastore URL
            prop    (str): Name of the property as defined by the vSphere SDK API

        Returns:
            The requested property value

        """
        # Search is done by using the 'info.name' and 'info.url' properties
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        # 
        property_names = ['info.name', 'info.url', prop]

        # Check if we are connected first
        if not self.viserver.is_connected():
            self.reconnect()
        
        syslog.syslog('[%s] Retrieving %s for datastore %s' % (self.vcenter, prop, name))

        # TODO: Custom zabbix properties and convertors
        # TODO: Exceptions, e.g. pysphere.resources.vi_exception.VIApiException:
        # TODO: See if you can optimize this and directly find the host instead of searching for it
        
        results = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                               obj_type=MORTypes.Datastore)
        
        # Iterate over the results and find our datastore with 'name' and 'url'
        for item in results:
            props = [(p.Name, p.Val) for p in item.PropSet]
            d = dict(props)

            # return the result back to Zabbix if we have a match
            if d['info.name'] == name and d['info.url'] == url:
                break
        else:
            return -1 # We didn't find the datastore we were looking for

        return { "status": 0, "datastore": name, "property": prop, "value": d[prop] } # Return the requested property
    
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
        self.backend.bind("tcp://*:15556")

        # Start the proxy
        syslog.syslog("Starting the VMPoller Proxy")
        zmq.proxy(self.frontend, self.backend)

        # This is never reached...
        self.frontend.close()
        self.backend.close()
        self.zcontext.term()
