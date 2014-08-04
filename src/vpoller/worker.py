# Copyright (c) 2013-2014 Marin Atanasov Nikolov <dnaeon@gmail.com>
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
vPoller Worker module for the VMware vSphere Poller

"""   

import os
import types
import logging
import ConfigParser
from time import time, asctime

import zmq
from vpoller.core import VPollerException
from vpoller.core import VPollerPeriodTask
from vpoller.agent import VSphereAgent
from vpoller.daemon import Daemon
from vconnector.core import VConnectorDatabase

class VPollerWorker(Daemon):
    """
    VPollerWorker class

    Prepares all vSphere Agents for polling from the vSphere hosts.

    This is the main vPoller Worker, which runs the vSphere Agents
    
    Extends:
        Daemon class

    Overrides:
        run() method

    """
    def run(self, config):
        """
        The main worker method.

        Args:
            config (str): Path to the confuguration file for vPoller Worker

        """
        logging.debug('Preparing vPoller Worker for start up')

        # Note the time we start up
        self.running_since = asctime()
        
        # A flag to signal that our daemon should be terminated
        self.time_to_die = False
        
        # Load the configuration file of the vPoller Worker
        self.load_worker_config(config)
        
        # Create the worker sockets
        self.create_worker_sockets()

        # Spawn the vSphere Agents of the Worker
        self.init_vsphere_agents()

        # Start the vSphere Agents
        self.connect_vsphere_agents()

        # Enter the main daemon loop from here
        logging.debug('Entering main daemon loop')
        while not self.time_to_die:
            socks = dict(self.zpoller.poll(1000))

            # Worker socket, receives client messages for processing
            #
            # The routing envelope of the message looks like this:
            #
            # Frame 1: [ N ][...]  <- Identity of connection
            # Frame 2: [ 0 ][]     <- Empty delimiter frame
            # Frame 3: [ N ][...]  <- Data frame
            if socks.get(self.worker_socket) == zmq.POLLIN:
                _id    = self.worker_socket.recv()
                _empty = self.worker_socket.recv()

                try:
                    msg = self.worker_socket.recv_json()
                except Exception as e:
                    logging.warning('Received bad client message, request will be ignored: %s', e)
                    continue

                result = self.process_client_msg(msg)
                
                # Return result back to client
                self.worker_socket.send(_id, zmq.SNDMORE)
                self.worker_socket.send("", zmq.SNDMORE)
                try:
                    self.worker_socket.send_json(result)
                except TypeError as e:
                    logging.warning('Cannot serialize result: %s', e)
                    self.worker_socket.send_json({ 'success': 1, 'msg': 'Cannot serialize result: %s' % e})

            # Management socket
            if socks.get(self.mgmt_socket) == zmq.POLLIN:
                msg = self.mgmt_socket.recv_json()
                result = self.process_mgmt_msg(msg)
                self.mgmt_socket.send_json(result)

        # Shutdown time has arrived, let's clean up a bit
        logging.debug('Shutdown time has arrived, vPoller Worker is going down')
        self.close_worker_sockets()
        self.disconnect_vsphere_agents()
        self.stop()

    def load_worker_config(self, config):
        """
        Loads the vPoller Worker configuration file

        Args:
            config (str): Path to the config file of vPoller Worker

        Raises:
            VPollerException

        """
        logging.debug('Loading vPoller Worker config file %s', config)

        if not os.path.exists(config):
            logging.error('Configuration file does not exists: %s', config)
            raise VPollerException, 'Configuration file does not exists: %s' % config

        parser = ConfigParser.ConfigParser()
        parser.read(config)

        try:
            self.connector_db   = parser.get('worker', 'db')
            self.proxy_endpoint = parser.get('worker', 'proxy')
            self.mgmt_endpoint  = parser.get('worker', 'mgmt')
        except ConfigParser.NoOptionError as e:
            logging.error('Configuration issues detected in %s: %s' , config, e)
            raise
        
    def create_worker_sockets(self):
        """
        Creates the ZeroMQ sockets used by the Worker

        Creates two sockets: 

        * REP socket (mgmt_socket) used for management
        * DEALER socket (worker_socket) connected to the VPoller Proxy

        Raises:
            VPollerException

        """
        logging.debug('Creating vPoller Worker sockets')

        self.zcontext = zmq.Context()
        
        self.mgmt_socket = self.zcontext.socket(zmq.REP)
        self.mgmt_socket.bind(self.mgmt_endpoint)

        logging.info('Connecting to the vPoller Proxy server')
        self.worker_socket = self.zcontext.socket(zmq.DEALER)
        self.worker_socket.connect(self.proxy_endpoint)

        # Create a poll set for our sockets
        logging.debug('Creating poll set for vPoller Worker sockets')
        self.zpoller = zmq.Poller()
        self.zpoller.register(self.mgmt_socket, zmq.POLLIN)
        self.zpoller.register(self.worker_socket, zmq.POLLIN)

    def close_worker_sockets(self):
        """
        Closes the ZeroMQ sockets used by the Worker

        """
        logging.debug('Closing vPoller Worker sockets')
        
        self.zpoller.unregister(self.mgmt_socket)
        self.zpoller.unregister(self.worker_socket)
        
        self.mgmt_socket.close()
        self.worker_socket.close()
        self.zcontext.term()

    def init_vsphere_agents(self):
        """
        Prepares the vSphere Agents used by the vPoller Worker

        """
        logging.debug('Initializing vSphere Agents')

        self.agents = dict()

        db = VConnectorDatabase(self.connector_db)
        db_agents = db.get_agents(only_enabled=True)

        if not db_agents:
            logging.warning('No registered or enabled vSphere Agents found')
            raise VPollerException, 'No registered or enabled vSphere Agents found'

        for each_agent in db_agents:
            agent = VSphereAgent(
                user=each_agent['user'],
                pwd=each_agent['pwd'],
                host=each_agent['host']
            )
            self.agents[agent.host] = agent

    def connect_vsphere_agents(self):
        """
        Connects all vSphere Agents to their respective VMware vSphere hosts

        """
        logging.debug('Starting vSphere Agents')
        
        for agent in self.agents:
            self.agents[agent].connect()

        self.agents_heartbeat_task = VPollerPeriodTask(
            interval=60,
            callback=self.keep_vsphere_agents_alive,
        )
        self.agents_heartbeat_task.run()

    def disconnect_vsphere_agents(self):
        """
        Disconnects all vPoller Agents from their respective VMware vSphere hosts
        
        """
        logging.debug('Shutting down vSphere Agents')

        for agent in self.agents:
            self.agents[agent].disconnect()

        self.agents_heartbeat_task.cancel()
            
    def keep_vsphere_agents_alive(self):
        """
        Dummy method to keep our vSphere Agents alive
        
        This dummy method calls CurrentTime() vSphere method
        in order to keep the connection to the vSphere host alive.

        Use a VPollerPeriodTask instance in order to invoke this function
        at a certain interval.
        
        """
        for agent in self.agents:
            logging.debug('[%s] Agent keep-alive heartbeat', self.agents[agent].host)
            self.agents[agent].si.CurrentTime()

    def process_client_msg(self, msg):
        """
        Processes a client message received on the vPoller Worker socket
    
        The message is passed to the VSphereAgent object of the respective vSphere host
        in order to do the actual polling.

        An example message for discovering the hosts could be:

            {
                "method":   "host.discover",
                "hostname": "vc01.example.org",
            }
       
        An example message for polling a datastore property could be:

            {
                "method":   "datastore.poll",
                "hostname": "vc01.example.org",
                "info.url": "ds:///vmfs/volumes/5190e2a7-d2b7c58e-b1e2-90b11c29079d/",
                "property": "summary.capacity"
            }

        Args:
        msg (dict): Client message for processing
        
        """
        logging.debug('Processing client message: %s', msg)

        if not isinstance(msg, dict):
            return { 'success': 1, 'msg': 'Expected a JSON message, received %s' % msg.__class__ }

        vsphere_host = msg.get('hostname')
        
        if not self.agents.get(vsphere_host):
            return { 'success': 1, 'msg': 'Unknown or missing vSphere Agent requested' }

        # The methods that the vSphere Agents support and process
        # In the below dict the key is the method name requested by the client,
        # where 'method' is the actual method invoked and the 'msg_attr' key is a
        # tuple/list of required attributes the message must have in order for this
        # request to be passed to and processed by the vSphere Agent
        methods = {
            'about': {
                'method':   self.agents[vsphere_host].about,
                'msg_attr': ('method', 'hostname'),
            },
            'event.latest': {
                'method':    self.agents[vsphere_host].event_latest,
                'msg_attr':  ('method', 'hostname'),
            },
            'net.discover': {
                'method':    self.agents[vsphere_host].net_discover,
                'msg_attr':  ('method', 'hostname'),
            },
            'net.get': {
                'method':    self.agents[vsphere_host].net_get,
                'msg_attr':  ('method', 'hostname', 'name'),
            },
            'net.host.get': {
                'method':    self.agents[vsphere_host].net_host_get,
                'msg_attr':  ('method', 'hostname', 'name'),
            },
            'net.vm.get': {
                'method':    self.agents[vsphere_host].net_vm_get,
                'msg_attr':  ('method', 'hostname', 'name'),
            },
            'datacenter.discover': {
                'method':    self.agents[vsphere_host].datacenter_discover,
                'msg_attr':  ('method', 'hostname'),
            },
            'datacenter.get': {
                'method':    self.agents[vsphere_host].datacenter_get,
                'msg_attr':  ('method', 'hostname', 'name', 'properties'),
            },
            'cluster.discover': {
                'method':    self.agents[vsphere_host].cluster_discover,
                'msg_attr':  ('method', 'hostname'),
            },
            'cluster.get': {
                'method':    self.agents[vsphere_host].cluster_get,
                'msg_attr':  ('method', 'hostname', 'name', 'properties'),
            },
            'resource.pool.discover': {
                'method':    self.agents[vsphere_host].resource_pool_discover,
                'msg_attr':  ('method', 'hostname'),
            },
            'resource.pool.get': {
                'method':    self.agents[vsphere_host].resource_pool_get,
                'msg_attr':  ('method', 'hostname', 'name', 'properties'),
            },
            'host.discover': {
                'method':    self.agents[vsphere_host].host_discover,
                'msg_attr':  ('method', 'hostname'),
            },
            'host.get': {
                'method':    self.agents[vsphere_host].host_get,
                'msg_attr':  ('method', 'hostname', 'name', 'properties'),
            },
            'host.cluster.get': {
                'method':    self.agents[vsphere_host].host_cluster_get,
                'msg_attr':  ('method', 'hostname', 'name'),
            },
            'host.vm.get': {
                'method':    self.agents[vsphere_host].host_vm_get,
                'msg_attr':  ('method', 'hostname', 'name'),
            },
            'host.datastore.get': {
                'method':    self.agents[vsphere_host].host_datastore_get,
                'msg_attr':  ('method', 'hostname'),
            },
            'host.net.get': {
                'method':    self.agents[vsphere_host].host_net_get,
                'msg_attr':  ('method', 'hostname', 'name'),
            },
            'vm.discover': {
                'method':    self.agents[vsphere_host].vm_discover,
                'msg_attr':  ('method', 'hostname'),
            },
            'vm.disk.discover': {
                'method':    self.agents[vsphere_host].vm_disk_discover,
                'msg_attr':  ('method', 'hostname', 'name'),
            },
            'vm.get': {
                'method':    self.agents[vsphere_host].vm_get,
                'msg_attr':  ('method', 'hostname', 'name', 'properties'),
            },
            'vm.datastore.get': {
                'method':    self.agents[vsphere_host].vm_datastore_get,
                'msg_attr':  ('method', 'hostname', 'name'),
            },
            'vm.disk.get': {
                'method':    self.agents[vsphere_host].vm_disk_get,
                'msg_attr':  ('method', 'hostname', 'name', 'key'),
            },
            'vm.host.get': {
                'method':    self.agents[vsphere_host].vm_host_get,
                'msg_attr':  ('method', 'hostname', 'name'),
            },
            'vm.guest.net.get': {
                'method':    self.agents[vsphere_host].vm_guest_net_get,
                'msg_attr':  ('method', 'hostname', 'name'),
            },
            'vm.net.get': {
                'method':    self.agents[vsphere_host].vm_net_get,
                'msg_attr':  ('method', 'hostname', 'name'),
            },
            'vm.process.get': {
                'method':    self.agents[vsphere_host].vm_process_get,
                'msg_attr':  ('method', 'hostname', 'name', 'username', 'password'),
            },
            'vm.cpu.usage.percent': {
                'method':    self.agents[vsphere_host].vm_cpu_usage_percent,
                'msg_attr':  ('method', 'hostname', 'name'),
            },
            'datastore.discover': {
                'method':    self.agents[vsphere_host].datastore_discover,
                'msg_attr':  ('method', 'hostname'),
            },
            'datastore.get': {
                'method':    self.agents[vsphere_host].datastore_get,
                'msg_attr':  ('method', 'hostname', 'name', 'properties'),
            },
            'datastore.host.get': {
                'method':    self.agents[vsphere_host].datastore_host_get,
                'msg_attr':  ('method', 'hostname', 'name'),
            },
            'datastore.vm.get': {
                'method':    self.agents[vsphere_host].datastore_vm_get,
                'msg_attr':  ('method', 'hostname', 'name'),
            },
        }

        if msg['method'] not in methods:
            return { 'success': 1, 'msg': 'Unknown method received' }

        agent_method  = methods[msg['method']]

        logging.debug('Checking client message, required to have: %s', agent_method['msg_attr'])

        # The message attributes type we expect to receive
        msg_attr_types = {
            'method':     (types.StringType, types.UnicodeType),
            'hostname':   (types.StringType, types.UnicodeType),
            'name':       (types.StringType, types.UnicodeType, types.NoneType),
            'key':        (types.StringType, types.UnicodeType, types.NoneType),
            'username':   (types.StringType, types.UnicodeType, types.NoneType),
            'password':   (types.StringType, types.UnicodeType, types.NoneType),
            'properties': (types.TupleType,  types.ListType, types.NoneType),
        }

        # Check if we have the required message attributes
        if not all (k in msg for k in agent_method['msg_attr']):
            return { 'success': 1, 'msg': 'Missing message attributes' }

        # Check if we have correct types of the message attributes
        for k in msg.keys():
            if not isinstance(msg[k], msg_attr_types.get(k, types.NoneType)):
                return { 'success': 1, 'msg': 'Incorrect message attribute type received' }
            
        # Process client request
        result = agent_method['method'](msg)

        return result

    def process_mgmt_msg(self, msg):
        """
        Processes a message for the management interface
        
        Example client message to shutdown the vPoller Worker would be:
        
            {
                "method": "worker.shutdown"
            }

        Getting status information from the vPoller worker:

            {
                "method": "worker.status"
            }

        Args:
            msg (dict): The client message for processing
              
        """
        logging.debug('Processing management message: %s', msg)

        if 'method' not in msg:
            return { 'success': 1, 'msg': 'Missing method name' } 
        
        # The vPoller Worker management methods we support and process
        methods = {
            'worker.status':   self.get_worker_status,
            'worker.shutdown': self.worker_shutdown,
        }
        
        if msg['method'] not in methods:
            return { 'success': 1, 'msg': 'Unknown method received' }

        # Process management request and return result to client
        result = methods[msg['method']](msg)

        return result
 
    def get_worker_status(self, msg):
        """
        Get status information about the vPoller Worker

        Args:
            msg (dict): The client message for processing (ignored)

        Returns:
            Status information about the vPoller Worker
            
        """
        logging.debug('Getting vPoller Worker status')

        result = {
            'success': 0,
            'msg': 'vPoller Worker Status',
            'result': {
                'status': 'running',
                'hostname': os.uname()[1],
                'proxy_endpoint': self.proxy_endpoint,
                'mgmt_endpoint': self.mgmt_endpoint,
                'connector_db': self.connector_db,
                'vsphere_agents': self.agents.keys(),
                'running_since': self.running_since,
                'uname': ' '.join(os.uname()),
            }
        }

        logging.debug('Returning result to client: %s', result)

        return result

    def worker_shutdown(self, msg):
        """
        Shutdown the vPoller Worker

        Args:
            msg (dict): The client message for processing (ignored)

        """
        logging.info('vPoller Worker is shutting down')

        self.time_to_die = True

        return { 'success': 0, 'msg': 'vPoller Worker is shutting down' }
