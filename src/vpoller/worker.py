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
import glob
import logging
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

    This is the main vPoller worker, which contains the vSphere Agents
    
    Extends:
        Daemon class

    Overrides:
        run() method

    """
    def run(self, config_file):
        """
        The main worker method.

        Args:
            config_file (str):  Configuration file for the VPollerWorker

        """
        # Note the time we start up
        self.running_since = asctime()
        
        # A flag to signal that our daemon should be terminated
        self.time_to_die = False
        
        # Load the configuration file of the vPoller Worker
        self.load_worker_config(config_file)
        
        # Create the worker sockets
        self.create_worker_sockets()

        # Spawn the vSphere Agents of the Worker
        self.spawn_vsphere_agents()

        # Start the vSphere Agents
        self.start_vsphere_agents()

        # Enter the main daemon loop from here
        while not self.time_to_die:
            socks = dict(self.zpoller.poll())

            # Worker socket, receives client messages for processing
            if socks.get(self.worker_socket) == zmq.POLLIN:
                # The routing envelope looks like this:
                #
                # Frame 1:  [ N ][...]  <- Identity of connection
                # Frame 2:  [ 0 ][]     <- Empty delimiter frame
                # Frame 3:  [ N ][...]  <- Data frame
                _id    = self.worker_socket.recv()
                _empty = self.worker_socket.recv()
                msg    = self.worker_socket.recv_json()

                # Process the client message and send the result
                result = self.process_client_message(msg)
                self.worker_socket.send(_id, zmq.SNDMORE)
                self.worker_socket.send("", zmq.SNDMORE)
                self.worker_socket.send_json(result)

            # Management socket
            if socks.get(self.mgmt_socket) == zmq.POLLIN:
                msg = self.mgmt_socket.recv_json()
                result = self.process_mgmt_message(msg)
                self.mgmt_socket.send_json(result)

        # Shutdown time has arrived, let's clean up a bit
        self.close_worker_sockets()
        self.shutdown_vsphere_agents()
 #       self.zcontext.term()
        self.stop()

    def load_worker_config(self, config_file):
        """
        Loads the vPoller Worker configuration file

        Args:
            config_file (str): Config file of the Worker

        Raises:
            VPollerException

        """
        if not os.path.exists(config_file):
            logging.error("Configuration file does not exists: %s", config_file)
            raise VPollerException, "Configuration file does not exists: %s" % config_file

        config = ConfigParser.ConfigParser()
        config.read(config_file)

        try:
            self.proxy_endpoint    = config.get('Default', 'proxy')
            self.mgmt_endpoint     = config.get('Default', 'mgmt')
            self.vsphere_hosts_dir = config.get('Default', 'vsphere_hosts_dir')
        except ConfigParser.NoOptionError as e:
            logging.error("Configuration issues detected in %s: %s" , config_file, e)
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
        self.zcontext = zmq.Context()
        
        # A management socket used to control the vPoller Worker daemon
        self.mgmt_socket = self.zcontext.socket(zmq.REP)

        try:
            self.mgmt_socket.bind(self.mgmt_endpoint)
        except zmq.ZMQError as e:
            logging.error("Cannot bind management socket: %s", e)
            raise VPollerException, "Cannot bind management socket: %s" % e

        # Create a DEALER socket for processing client messages
        logging.info("Connecting to the vPoller Proxy server")
        self.worker_socket = self.zcontext.socket(zmq.DEALER)

        try:
            self.worker_socket.connect(self.proxy_endpoint)
        except zmq.ZMQError as e:
            logging.error("Cannot connect worker to vPoller Proxy: %s", e)
            raise VPollerException, "Cannot connect worker to vPoller Proxy: %s" % e

        # Create a poll set for our sockets
        self.zpoller = zmq.Poller()
        self.zpoller.register(self.mgmt_socket, zmq.POLLIN)
        self.zpoller.register(self.worker_socket, zmq.POLLIN)

    def close_worker_sockets(self):
        """
        Closes the ZeroMQ sockets used by the Worker

        """
        self.zpoller.unregister(self.mgmt_socket)
        self.zpoller.unregister(self.worker_socket)
        self.mgmt_socket.close()
        self.worker_socket.close()

    def spawn_vsphere_agents(self):
        """
        Prepares the vSphere Agent objects used by the Worker

        """
        # Get the configuration files for our vSphere hosts
        confFiles = self.get_vsphere_configs(self.vsphere_hosts_dir)
 
        self.agents = dict()

        # Load the config for every vSphere Agent
        for eachConf in confFiles:
            agent = VSphereAgent(eachConf, ignore_locks=True, lockdir="/var/run/vpoller", keep_alive=True)
            self.agents[agent.hostname] = agent

    def start_vsphere_agents(self):
        """
        Connects all VPoller Agents to their respective vSphere hosts

        """
        for eachAgent in self.agents:
            try:
                self.agents[eachAgent].connect()
            except Exception as e:
                logging.error('Cannot connect to %s: %s', eachAgent, e)

    def shutdown_vsphere_agents(self):
        """
        Disconnects all VPoller Agents from their respective vSphere hosts
        
        """
        for eachAgent in self.agents:
            self.agents[eachAgent].disconnect()
        
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
        if not os.path.exists(config_dir) or not os.path.isdir(config_dir):
            logging.error("%s does not exists or is not a directory", config_dir)
            raise VPollerException, "%s does not exists or is not a directory" % config_dir
        
        # Get all *.conf files for the hosts
        path = os.path.join(config_dir, "*.conf")
        confFiles = glob.glob(path)

        if not confFiles:
            logging.error("No vSphere config files found in %s", config_dir)
            raise VPollerException, "No vSphere config files found in %s" % config_dir

        return confFiles

    def process_client_message(self, msg):
        """
        Processes a client request message

        The message is passed to the VSphereAgent object of the respective vSphere host
        in order to do the actual polling.

        The messages that we support are polling for datastores and hosts.

        An example message for discovering the hosts could be:

            {
              "method":   "host.discover",
              "hostname": "vc01-test.example.org",
            }

        An example message for polling a datastore property could be:

            {
              "method":   "datastore.poll",
              "hostname": "vc0-test.example.org",
              "info.url": "ds:///vmfs/volumes/5190e2a7-d2b7c58e-b1e2-90b11c29079d/",
              "property": "summary.capacity"
              }

        Args:
            msg (dict): The client message for processing

        """
        # We require to have at least the 'method' and vSphere 'hostname'
        if not all(k in msg for k in ("method", "hostname")):
            return { "success": -1, "msg": "Missing message properties (e.g. method/hostname)" }

        vsphere_host = msg["hostname"]

        if not self.agents.get(vsphere_host):
            return { "success": -1, "msg": "Unknown vSphere Agent requested" }

        # The methods we support and process
        methods = {
            'host.poll':            self.agents[vsphere_host].get_host_property,
            'host.discover':        self.agents[vsphere_host].discover_hosts,
            'datastore.poll':       self.agents[vsphere_host].get_datastore_property,
            'datastore.discover':   self.agents[vsphere_host].discover_datastores,
            'vm.poll':              self.agents[vsphere_host].get_vm_property,
            'vm.discover':          self.agents[vsphere_host].discover_virtual_machines,
            'datacenter.poll':      self.agents[vsphere_host].get_datacenter_property,
            'datacenter.discover':  self.agents[vsphere_host].discover_datacenters,
            }

        result = methods[msg['method']](msg) if methods.get(msg['method']) else { "success": -1, "msg": "Unknown command received" }

        return result
        
    def process_mgmt_message(self, msg):
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
        if not "method" in msg:
            return { "success": -1, "msg": "Missing method name" }
        
        # The management methods we support and process
        methods = {
            'worker.status':   self.get_worker_status,
            'worker.shutdown': self.worker_shutdown,
            }
        
        result = methods[msg['method']](msg) if methods.get(msg['method']) else { "success": -1, "msg": "Uknown command received" }

        return result
 
    def get_worker_status(self, msg):
        """
        Get status information about the vPoller Worker

        Args:
            msg (dict): The client message for processing (ignored)

        Returns:
            Status information about the vPoller Worker
            
        """

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

        return result

    def worker_shutdown(self, msg):
        """
        Shutdown the vPoller Worker

        Args:
            msg (dict): The client message for processing (ignored)

        """
        logging.info("vPoller Worker is shutting down")

        self.time_to_die = True

        return { "success": 0, "msg": "vPoller Worker is shutting down" }
