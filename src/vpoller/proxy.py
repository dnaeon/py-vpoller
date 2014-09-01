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
vPoller Proxy module for the VMware vSphere Poller

"""

import os
import logging
import ConfigParser
import multiprocessing

import zmq
from vpoller.core import VPollerException

class VPollerProxyManager(object):
    """
    Manager of vPoller Proxy

    """
    def __init__(self, config_file):
        """
        Initializes a new vPoller Proxy Manager

        Args:
            config_file (str): Path to the vPoller configuration file

        """
        self.config_file = config_file
        self.config = {}
        self.config_defaults = {
            'mgmt': 'tcp://*:9999',
            'frontend': 'tcp://*:10123',
            'backend': 'tcp://*:10124',
        }
        self.time_to_die = multiprocessing.Event()
        self.zcontext = None
        self.zpoller = None
        self.mgmt_socket = None
        self.mgmt_methods = {
            'status': self.status,
            'shutdown': self.signal_stop,
        }
        self.proxy = None

    def start(self):
        """
        Start the vPoller Proxy processes

        """
        logging.info('Starting vPoller Proxy Manager')

        self.load_config()
        self.create_sockets()
        self.start_proxy_process()

        while not self.time_to_die.is_set():
            self.wait_for_mgmt_task()

        self.stop()

    def stop(self):
        """
        Stop the vPoller Proxy processes

        """
        self.close_sockets()
        self.stop_proxy_process()


    def signal_stop(self):
        """
        Signal the vPoller Proxy Manager that shutdown time has arrived

        """
        self.time_to_die.set()

        return { 'success': 0, 'msg': 'Shutdown time has arrived' }

    def load_config(self):
        """
        Load the vPoller Proxy Manager configuration settings
        
        """
        logging.debug('Loading config file %s', self.config_file)

        parser = ConfigParser.ConfigParser(self.config_defaults)
        parser.read(self.config_file)

        self.config['mgmt'] = parser.get('proxy', 'mgmt')
        self.config['frontend'] = parser.get('proxy', 'frontend')
        self.config['backend'] = parser.get('proxy', 'backend')

    def start_proxy_process(self):
        """
        Start the vPoller Proxy process

        """
        logging.info('Starting vPoller Proxy process')
        
        self.proxy = VPollerProxy(
            frontend=self.config.get('frontend'),
            backend=self.config.get('backend')
        )
        self.proxy.daemon = True
        self.proxy.start()
            
    def stop_proxy_process(self):
        """
        Stop the vPoller Proxy process
        
        """
        logging.info('Stopping vPoller Proxy process')
        
        self.proxy.signal_stop()
        self.proxy.join(3)

    def create_sockets(self):
        """
        Creates the ZeroMQ sockets used by the vPoller Proxy Manager

        """
        self.zcontext = zmq.Context()
        self.mgmt_socket = self.zcontext.socket(zmq.REP)
        self.mgmt_socket.bind(self.config.get('mgmt'))
        self.zpoller = zmq.Poller()
        self.zpoller.register(self.mgmt_socket, zmq.POLLIN)

    def close_sockets(self):
        """
        Closes the ZeroMQ sockets used by the vPoller Proxy Manager

        """
        logging.info('Closing vPoller Proxy Manager sockets')

        self.zpoller.unregister(self.mgmt_socket)
        self.mgmt_socket.close()
        self.zcontext.term()
        
    def wait_for_mgmt_task(self):
        """
        Poll the management socket for management tasks

        """
        socks = dict(self.zpoller.poll())
        if socks.get(self.mgmt_socket) == zmq.POLLIN:
            try:
                msg = self.mgmt_socket.recv_json()
            except TypeError as e:
                logging.warning('Invalid message received on management interface: %s', msg)
                return

            result = self.process_mgmt_task(msg)
            self.mgmt_socket.send_json(result)

    def process_mgmt_task(self, msg):
        """
        Processes a message for the management interface
       
        Example client message to shutdown the vPoller Worker would be:
    
            {
                "method": "shutdown"
            }

        Args:
            msg (dict): The client message for processing

        """
        logging.debug('Processing management message: %s', msg)

        if 'method' not in msg:
            return { 'success': 1, 'msg': 'Missing method name' }

        if msg['method'] not in self.mgmt_methods:
            return { 'success': 1, 'msg': 'Uknown method name received' }

        method = msg['method']
        result = self.mgmt_methods[method]()

        return result

    def status(self):
        """
        Get status information about the vPoller Proxy

        """
        result = {
            'success': 0,
            'msg': 'vPoller Proxy status', 
            'result': {
                'status': 'running',
                'hostname': os.uname()[1],
                'mgmt': self.config.get('mgmt')
                'frontend': self.config.get('frontend'),
                'backend': self.config.get('backend'),
                'uname': ' '.join(os.uname()),
            }
        }

        return result

class VPollerProxy(Daemon):
    """
    VPoller Proxy class

    ZeroMQ proxy which load-balances client requests to a
    pool of connected vPoller Workers

    Extends:
        Daemon

    Overrides:
        run() method

    """
    def run(self, config):
        """
        The main vPoller Proxy method

        Args:
            config (str): Path to the config file for vPoller Proxy

        """
        logging.debug('Preparing vPoller Proxy for start up')
        
        # Note the time we start up
        self.running_since = asctime()

        # A flag to indicate that the vPoller Proxy daemon should be terminated
        self.time_to_die = False

        # Load the configuration file of the vPoller Proxy
        self.load_proxy_config(config)

        # Create vPoller Proxy sockets
        self.create_proxy_sockets()
        
        logging.info('Starting the VPoller Proxy')
        
        # Enter the main daemon loop from here
        logging.debug('Entering main daemon loop')
        while not self.time_to_die:
            socks = dict(self.zpoller.poll())

            # Frontend socket, forward messages to the backend
            if socks.get(self.frontend) == zmq.POLLIN:
                self.process_frontend_msg()
                
            # Backend socket, forward messages back to the clients
            if socks.get(self.backend) == zmq.POLLIN:
                self.process_backend_msg()

            # Management socket
            if socks.get(self.mgmt) == zmq.POLLIN:
                self.process_mgmt_msg()

        # Shutdown time has arrived, let's clean up a bit
        logging.debug('Shutdown time has arrived, vPoller Proxy is going down')
        self.close_proxy_sockets()
        self.stop()

    def load_proxy_config(self, config):
        """
        Loads the vPoller Proxy configuration file
        
        Args:
            config (str): Path to the config file of vPoller Proxy

        Raises:
            VPollerException
            
        """
        logging.debug('Loading vPoller Proxy configuration file %s', config)
        
        if not os.path.exists(config):
            logging.error('Configuration file does not exists: %s', config)
            raise VPollerException, 'Configuration file does not exists: %s' % config 

        parser = ConfigParser.ConfigParser()
        parser.read(config)

        try:
            self.frontend_endpoint = parser.get('proxy', 'frontend')
            self.backend_endpoint  = parser.get('proxy', 'backend')
            self.mgmt_endpoint     = parser.get('proxy', 'mgmt')
        except ConfigParser.NoOptionError as e:
            logging.error('Configuration issues detected in %s: %s', config, e)
            raise

    def create_proxy_sockets(self):
        """
        Creates the ZeroMQ sockets used by the vPoller Proxy

        Creates three sockets: 

        * REP socket (mgmt) used for management
        * ROUTER socket (frotend) facing clients
        * DEALER socket (backend) for workers

        Raises:
            VPollerException
            
        """
        logging.debug('Creating vPoller Proxy sockets')

        self.zcontext = zmq.Context()

        # vPoller Proxy sockets
        self.mgmt     = self.zcontext.socket(zmq.REP)
        self.frontend = self.zcontext.socket(zmq.ROUTER)
        self.backend  = self.zcontext.socket(zmq.DEALER)

        logging.debug('Binding vPoller Proxy sockets')

        try:
            self.mgmt.bind(self.mgmt_endpoint)
            self.frontend.bind(self.frontend_endpoint)
            self.backend.bind(self.backend_endpoint)
        except zmq.ZMQError as e:
            logging.error('Cannot bind vPoller Proxy sockets: %s', e)
            raise VPollerException, 'Cannot vPoller Proxy sockets: %s' % e

        # Create a poll set for our sockets
        logging.debug('Creating a poll set for vPoller Proxy sockets')
        self.zpoller = zmq.Poller()
        self.zpoller.register(self.mgmt, zmq.POLLIN)
        self.zpoller.register(self.frontend, zmq.POLLIN)
        self.zpoller.register(self.backend, zmq.POLLIN)

    def close_proxy_sockets(self):
        """
        Closes the ZeroMQ sockets used by vPoller Proxy

        """
        logging.debug('Closing vPoller Proxy sockets')

        self.zpoller.unregister(self.mgmt)
        self.zpoller.unregister(self.frontend)
        self.zpoller.unregister(self.backend)
        
        self.mgmt.close()
        self.frontend.close()
        self.backend.close()

        self.zcontext.term()

    def process_frontend_msg(self):
        """
        Processes a message on the frontend socket

        The received message is passed to backend socket
        for further processing by workers

        """
        logging.debug('Received message on frontend socket, passing to backend')
        
        msg = self.frontend.recv()
        more = self.frontend.getsockopt(zmq.RCVMORE)
        if more:
            self.backend.send(msg, zmq.SNDMORE)
        else:
            self.backend.send(msg)

    def process_backend_msg(self):
        """
        Processes a message on the backend socket

        The received message is passed to frontend socket
        which contains results for clients
        
        """
        logging.debug('Received message on backend socket, passing to frontend')

        msg = self.backend.recv()
        more = self.backend.getsockopt(zmq.RCVMORE)
        if more:
            self.frontend.send(msg, zmq.SNDMORE)
        else:
            self.frontend.send(msg)
        
    def process_mgmt_msg(self):
        """
        Processes a message for the management interface of VPoller Proxy

        An example message to get status information would be:

            {
                "method": "proxy.status"
            }

        An example message to shutdown the vPoller Proxy would be:

            {
                "method": "proxy.shutdown"
            }
        
        Args:
            msg (dict): The client message to process

        """
        logging.debug('Received message on management socket')

        msg = self.mgmt.recv_json()
        
        # Check if we have a command to process
        if 'method' not in msg:
            return { 'success': 1, 'msg': 'Missing method name' }

        # Methods the vPoller Proxy supports and processes
        methods = {
            'proxy.status':   self.get_proxy_status,
            'proxy.shutdown': self.proxy_shutdown,
        }

        if msg['method'] not in methods:
            return { 'success': 1, 'msg': 'Unknown method received' }

        # Process the requested method
        result = methods[msg['method']](msg)

        logging.debug('Sending result to client: %s', result)

        self.mgmt.send_json(result)

    def get_proxy_status(self, msg):
        """
        Get status information about the vPoller Proxy

        Args:
            msg (dict): The client message for processing (ignored)

        Returns:
            Status information about the vPoller Proxy
            
        """
        logging.debug('Getting vPoller Proxy status')

        result = {
            'success': 0,
            'msg': 'vPoller Proxy Status', 
            'result': {
                'status': 'running',
                'hostname': os.uname()[1],
                'frontend_endpoint': self.frontend_endpoint,
                'backend_endpoint': self.backend_endpoint,
                'mgmt_endpoint': self.mgmt_endpoint,
                'running_since': self.running_since,
                'uname': ' '.join(os.uname()),
            }
        }

        logging.debug('Sending result to client: %s', result)
        
        return result

    def proxy_shutdown(self, msg):
        """
        Shutdown the vPoller Worker

        Args:
            msg (dict): The client message for processing (ignored)

        """
        logging.info('vPoller Proxy is shutting down')

        self.time_to_die = True

        return { 'success': 0, 'msg': 'vPoller Proxy is shutting down' }

