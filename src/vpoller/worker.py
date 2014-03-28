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
import sqlite3
import ConfigParser
from time import asctime

import zmq
from vpoller.core import VPollerException
from vpoller.agent import VSphereAgent
from vpoller.daemon import Daemon

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
        self.spawn_vsphere_agents()

        # Start the vSphere Agents
        self.start_vsphere_agents()

        # Enter the main daemon loop from here
        logging.debug('Entering main daemon loop')
        while not self.time_to_die:
            socks = dict(self.zpoller.poll())

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
                msg    = self.worker_socket.recv_json()
                result = self.process_client_msg(msg)
                # Return result back to client
                self.worker_socket.send(_id, zmq.SNDMORE)
                self.worker_socket.send("", zmq.SNDMORE)
                self.worker_socket.send_json(result)

            # Management socket
            if socks.get(self.mgmt_socket) == zmq.POLLIN:
                msg = self.mgmt_socket.recv_json()
                result = self.process_mgmt_msg(msg)
                self.mgmt_socket.send_json(result)

        # Shutdown time has arrived, let's clean up a bit
        logging.debug('Shutdown time has arrived, vPoller Worker is going down')
        self.close_worker_sockets()
        self.shutdown_vsphere_agents()
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
        parser.read(config_file)

        try:
            self.worker_db      = parser.get('worker', 'db')
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

    def spawn_vsphere_agents(self):
        """
        Prepares the vSphere Agents used by the vPoller Worker

        """
        logging.debug('Spawning vSphere Agents')

        self.agents = dict()

        for each_agent in self.worker_db_get_agents(only_enabled=True):
            agent = VSphereAgent(
                user=each_agent['user'],
                pwd=each_agent['pwd'],
                host=each_agent['host']
            )
            self.agents[agent.host] = agent

    def start_vsphere_agents(self):
        """
        Connects all vSphere Agents to their respective VMware vSphere hosts

        """
        logging.debug('Starting vSphere Agents')
        
        for agent in self.agents:
            self.agents[agent].connect()

    def shutdown_vsphere_agents(self):
        """
        Disconnects all vPoller Agents from their respective VMware vSphere hosts
        
        """
        logging.debug('Shutting down vSphere Agents')

        for agent in self.agents:
            self.agents[agent].disconnect()
        
    def get_vsphere_configs(self, config_dir):
        """
        Gets the configuration files for the vSphere hosts
        
        The 'config_dir' argument should point to a directory containing all .conf files
        for the different hosts we are connecting our VSphereAgents to.
        
        Args:
            config_dir (str): A directory containing configuration files for the vSphere Agents

        Returns:
            A list of all configuration files found in the config directory
        
        Raises:
            VPollerException
            
        """
        logging.debug('Getting vSphere configuration files from: %s', config_dir)
        
        if not os.path.exists(config_dir) or not os.path.isdir(config_dir):
            logging.error('%s does not exists or is not a directory', config_dir)
            raise VPollerException, '%s does not exists or is not a directory' % config_dir
        
        # Get all *.conf files for the hosts
        path = os.path.join(config_dir, '*.conf')
        conf_files = glob.glob(path)

        if not conf_files:
            logging.error('No vSphere config files found in %s', config_dir)
            raise VPollerException, 'No vSphere config files found in %s' % config_dir

        logging.debug('Discovered vSphere configuration files: %s', conf_files)

        return conf_files

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

        vsphere_host = msg.get('hostname')
        
        if not self.agents.get(vsphere_host):
            return { 'success': -1, 'msg': 'Unknown vSphere Agent requested' }

        # The methods that the vSphere Agents support and process
        # In the below dict the key is the method name requested by the client,
        # where 'method' is the actual method invoked and the 'msg_attr' key is a
        # tuple/list of required attributes the message must have in order for this
        # request to be passed to and processed by the vSphere Agent
        methods = {
            'datacenter.discover':  {
                'method':    self.agents[vsphere_host].datacenter_discover,
                'msg_attr':  ('method', 'hostname'),
            },
        }

        if msg['method'] not in methods:
            return { 'success': -1, 'msg': 'Unknown method received' }

        agent_method  = methods[msg['method']]

        logging.debug('Checking client message, required to have: %s', agent_method['msg_attr'])

        # The message attributes type we expect to receive
        msg_attr_types = {
            'method':     (types.StringType, types.UnicodeType),
            'hostname':   (types.StringType, types.UnicodeType),
            'name':       (types.StringType, types.UnicodeType, types.NoneType),
            'properties': (types.TupleType,  types.ListType, types.NoneType),
        }

        # Check if we have the required message attributes
        if not all (k in msg for k in agent_method['msg_attr']):
            return { 'success': -1, 'msg': 'Missing message attributes' }

        # Check if we have correct types of the message attributes
        for k in msg.keys():
            if not isinstance(msg[k], msg_types[k]):
                return { 'success': -1, 'msg': 'Incorrect message attribute type received' }
            
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
            return { 'success': -1, 'msg': 'Missing method name' } 
        
        # The vPoller Worker management methods we support and process
        methods = {
            'worker.status':   self.get_worker_status,
            'worker.shutdown': self.worker_shutdown,
        }
        
        if msg['method'] not in methods:
            return { 'success': -1, 'msg': 'Unknown method received' }

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
                'vsphere_hosts_dir': self.vsphere_hosts_dir,
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

    def worker_db_init(self):
        """
        Initializes the vPoller Worker database

        The vPoller Worker database is used for storing
        configuration about our vSphere Agents, such as
        hostnames, usernames, passwords, etc.

        """
        logging.info('Initializing vPoller Worker database at %s', self.worker_db)

        if os.path.exists(self.worker_db):
            raise VPollerException, 'vPoller Worker database already exists at %s' % self.worker_db

        conn = sqlite3.connet(self.worker_db)
        cursor = conn.cursor()

        sql = """
        CREATE TABLE hosts (
            host TEXT UNIQUE,
            user TEXT,
            pwd  TEXT,
            enabled INTEGER
        )
        """

        cursor.execute(sql)
        cursor.close()

    def worker_db_add_update_agent(self, host, user, pwd, enabled):
        """
        Add/update a vSphere Agent in the vPoller Worker database

        Args:
            host    (str): Hostname of the vSphere host
            user    (str): Username to use when connecting
            pwd     (str): Password to use when connecting
            enabled (int): Enable or disable the vSphere Agent

        """
        logging.info('Adding/updating vSphere Agent %s in database', host)

        conn = sqlite3.connect(self.worker_db)
        cursor = conn.cursor()

        cursor.execute('INSERT OR REPLACE INTO hosts VALUES (?,?,?,?)', (host, user, pwd, enabled))
        cursor.commit()
        cursor.close()

    def worker_db_remove_agent(self, host):
        """
        Remove a vSphere Agent from the vPoller Worker database

        Args:
            host (str): Hostname of the vSphere Agent to remove
        
        """
        logging.info('Removing vSphere Agent %s from database', host)

        conn = sqlite3.connect(self.worker_db)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM hosts WHERE host = ?', host)
        cursor.commit()
        cursor.close()

    def worker_db_get_agents(self, only_enabled=False):
        """
        Get the vSphere Agents from the vPoller Worker database

        Args:
            only_enabled (bool): If True return only the Agents which are enabled

        """
        logging.debug('Getting vSphere Agents from database')

        conn = sqlite3.connect(self.worker_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if only_enabled:
            sql = 'SELECT * FROM hosts WHERE enabled = 1'
        else:
            sql = 'SELECT * FROM hosts'

        cursor.execute(sql)
        result = cursor.fetchall()
        cursor.close()

        return result
        
