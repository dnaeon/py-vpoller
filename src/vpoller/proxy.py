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
from time import asctime

import zmq
from vpoller.core import VPollerException
from vpoller.daemon import Daemon

class VPollerProxy(Daemon):
    """
    VPoller Proxy class

    ZeroMQ proxy/broker which load-balances all client requests to a
    pool of connected vPoller Workers workers.

    Extends:
        Daemon

    Overrides:
        run() method

    """
    def run(self, config_file):
        """
        The main vPoller Proxy method

        Args:
            config_file (str): Location to the config file for vPoller Proxy

        """
        # Note the time we start up
        self.running_since = asctime()

        # A flag to indicate that the VPollerProxy daemon should be terminated
        self.time_to_die = False

        # Load the configuration file of the vPoller Proxy
        self.load_proxy_config(config_file)

        # Create vPoller Proxy sockets
        self.create_proxy_sockets()
        
        logging.info("Starting the VPoller Proxy")
        
        # Enter the main daemon loop from here
        while not self.time_to_die:
            socks = dict(self.zpoller.poll())

            # Frontend socket, forward messages to the backend
            if socks.get(self.frontend) == zmq.POLLIN:
                msg = self.frontend.recv()
                more = self.frontend.getsockopt(zmq.RCVMORE)
                if more:
                    self.backend.send(msg, zmq.SNDMORE)
                else:
                    self.backend.send(msg)

            # Backend socket, forward messages back to the clients
            if socks.get(self.backend) == zmq.POLLIN:
                msg = self.backend.recv()
                more = self.backend.getsockopt(zmq.RCVMORE)
                if more:
                    self.frontend.send(msg, zmq.SNDMORE)
                else:
                    self.frontend.send(msg)

            # Management socket
            if socks.get(self.mgmt) == zmq.POLLIN:
                msg = self.mgmt.recv_json()
                result = self.process_mgmt_message(msg)
                self.mgmt.send(result)

        # Shutdown time has arrived, let's clean up a bit
        self.close_proxy_sockets()
#        self.zcontext.term()
        self.stop()

    def load_proxy_config(self, config_file):
        """
        Loads the vPoller Proxy configuration file
        
        Args:
            config_file (str): Config file of the vPoller Proxy

        Raises:
            VPollerException
            
        """
        if not os.path.exists(config_file):
            logging.error("Configuration file does not exists: %s", config_file)
            raise VPollerException, "Configuration file does not exists: %s" % config_file 

        config = ConfigParser.ConfigParser()
        config.read(config_file)

        try:
            self.frontend_endpoint = config.get('Default', 'frontend')
            self.backend_endpoint  = config.get('Default', 'backend')
            self.mgmt_endpoint     = config.get('Default', 'mgmt')
        except ConfigParser.NoOptionError as e:
            logging.error("Configuration issues detected in %s: %s", config_file, e)
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
        self.zcontext = zmq.Context()

        # A management socket, used to control the VPollerProxy daemon
        self.mgmt = self.zcontext.socket(zmq.REP)

        try:
            self.mgmt.bind(self.mgmt_endpoint)
        except zmq.ZMQError as e:
            logging.error("Cannot bind management socket: %s", e)
            raise VPollerException, "Cannot bind management socket: %s" % e
        
        # Socket facing clients
        self.frontend = self.zcontext.socket(zmq.ROUTER)

        try:
            self.frontend.bind(self.frontend_endpoint)
        except zmq.ZMQError as e:
            logging.error("Cannot bind frontend socket: %s", e)
            raise VPollerException, "Cannot bind frontend socket: %s" % e

        # Socket facing workers
        self.backend = self.zcontext.socket(zmq.DEALER)

        try:
            self.backend.bind(self.backend_endpoint)
        except zmq.ZMQError as e:
            logging.error("Cannot bind backend socket: %s", e)
            raise VPollerException, "Cannot bind backend socket: %s" % e

        # Create a poll set for our sockets
        self.zpoller = zmq.Poller()
        self.zpoller.register(self.frontend, zmq.POLLIN)
        self.zpoller.register(self.backend, zmq.POLLIN)
        self.zpoller.register(self.mgmt, zmq.POLLIN)

    def close_proxy_sockets(self):
        """
        Closes the ZeroMQ sockets used by the vPoller Proxy

        """
        self.zpoller.unregister(self.frontend)
        self.zpoller.unregister(self.backend)
        self.zpoller.unregister(self.mgmt)
        self.frontend.close()
        self.backend.close()
        self.mgmt.close()
        
    def process_mgmt_message(self, msg):
        """
        Processes a message for the management interface of the VPoller Proxy

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
        # Check if we have a command to process
        if not "method" in msg:
            return "{ \"success\": -1, \"msg\": \"Missing command name\" }"

        # Methods we support and process
        methods = {
            'proxy.status':   self.get_proxy_status(msg),
            'proxy.shutdown': self.proxy_shutdown(msg),
            }

        result = methods[msg['method']] if methods.get(msg['method']) else "{ \"status\": -1, \"msg\": \"Uknown command received\" }"

        return result

    def get_proxy_status(self, msg):
        """
        Get status information about the vPoller Proxy

        Args:
            msg (dict): The client message for processing (ignored)

        Returns:
            Status information about the vPoller Proxy
            
        """
        result = '{ "success": 0, \
                    "msg": "vPoller Proxy Status", \
                    "result": {\
                        "status": "running", \
                        "hostname": "%s", \
                        "frontend_endpoint": "%s", \
                        "backend_endpoint": "%s", \
                        "mgmt_endpoint": "%s", \
                        "running_since": "%s", \
                        "uname": "%s" \
                      } \
                  }' % (os.uname()[1],
                        self.frontend_endpoint,
                        self.backend_endpoint,
                        self.mgmt_endpoint,
                        self.running_since,
                        " ".join(os.uname()))
        return result

    def proxy_shutdown(self, msg):
        """
        Shutdown the vPoller Worker

        Args:
            msg (dict): The client message for processing (ignored)

        """
        logging.info("vPoller Proxy is shutting down")

        self.time_to_die = True

        return "{ \"success\": 0, \"msg\": \"vPoller Proxy is shutting down\" }"

