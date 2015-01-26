# Copyright (c) 2013-2015 Marin Atanasov Nikolov <dnaeon@gmail.com>
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

import multiprocessing

from platform import node

try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser

import zmq

from vpoller import __version__
from vpoller.log import logger


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
        self.node = node()
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
        logger.info('Starting Proxy Manager [%s release]', __version__)

        self.load_config()
        self.create_sockets()
        self.start_proxy_process()

        logger.info('Proxy Manager is ready and running')
        while not self.time_to_die.is_set():
            try:
                self.wait_for_mgmt_task()
            except KeyboardInterrupt:
                self.signal_stop()

        self.stop()

    def stop(self):
        """
        Stop the vPoller Proxy processes

        """
        logger.info('Proxy Manager is shutting down')
        self.close_sockets()
        self.stop_proxy_process()

    def signal_stop(self):
        """
        Signal the Proxy Manager that shutdown time has arrived

        """
        logger.info('Received shutdown signal')
        self.time_to_die.set()
        
        return {'success': 0, 'msg': 'Shutdown time has arrived'}

    def load_config(self):
        """
        Load the vPoller Proxy Manager configuration settings

        """
        logger.debug('Loading config file %s', self.config_file)

        parser = ConfigParser(self.config_defaults)
        parser.read(self.config_file)

        self.config['mgmt'] = parser.get('proxy', 'mgmt')
        self.config['frontend'] = parser.get('proxy', 'frontend')
        self.config['backend'] = parser.get('proxy', 'backend')

        logger.debug(
            'Proxy Manager configuration: %s',
            self.config
        )

    def start_proxy_process(self):
        """
        Start the vPoller Proxy process

        """
        logger.info('Starting Proxy process')

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
        logger.info('Stopping Proxy process')

        self.proxy.signal_stop()
        self.proxy.join(3)

    def create_sockets(self):
        """
        Creates the ZeroMQ sockets used by the vPoller Proxy Manager

        """
        logger.info('Creating Proxy Manager sockets')
        self.zcontext = zmq.Context()
        self.mgmt_socket = self.zcontext.socket(zmq.REP)
        self.mgmt_socket.bind(self.config.get('mgmt'))
        self.zpoller = zmq.Poller()
        self.zpoller.register(self.mgmt_socket, zmq.POLLIN)

    def close_sockets(self):
        """
        Closes the ZeroMQ sockets used by the vPoller Proxy Manager

        """
        logger.info('Closing Proxy Manager sockets')
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
            except TypeError:
                logger.warning(
                    'Invalid management message received',
                )
                self.mgmt_socket.send('Invalid message received')
                return

            result = self.process_mgmt_task(msg)
            self.mgmt_socket.send_json(result)

    def process_mgmt_task(self, msg):
        """
        Processes a message for the management interface

        Example client message to shutdown Proxy Manager would be:

            {
                "method": "shutdown"
            }

        Args:
            msg (dict): The client message for processing

        """
        logger.debug('Processing management message: %s', msg)

        if 'method' not in msg:
            return {
                'success': 1,
                'msg': 'Missing method name'
            }

        if msg['method'] not in self.mgmt_methods:
            return {
                'success': 1,
                'msg': 'Uknown method name received'
            }

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
                'hostname': self.node,
                'mgmt': self.config.get('mgmt'),
                'frontend': self.config.get('frontend'),
                'backend': self.config.get('backend'),
            }
        }

        return result


class VPollerProxy(multiprocessing.Process):
    """
    VPollerProxy class

    A ZeroMQ proxy which distributes tasks to connected workers

    Extends:
        multiprocessing.Process

    Overrides:
        run() method

    """
    def __init__(self, frontend, backend):
        """
        Initialize a new VPollerProxy process

        Args:
            frontend (str): Endpoint to which clients connect
            backend  (str): Endpoint to which workers connect

        """
        super(VPollerProxy, self).__init__()
        self.time_to_die = multiprocessing.Event()
        self.config = {
            'frontend': frontend,
            'backend': backend,
            }
        self.zcontext = None
        self.zpoller = None
        self.frontend = None
        self.backend = None

    def run(self):
        logger.info('Proxy process is starting')

        self.create_sockets()

        logger.info('Proxy process is ready and running')
        while not self.time_to_die.is_set():
            try:
                self.distribute_tasks()
            except KeyboardInterrupt:
                self.signal_stop()

        self.stop()

    def stop(self):
        """
        Stop the vPoller Proxy process

        """
        logger.info('Proxy process is shutting down')
        self.close_sockets()

    def signal_stop(self):
        """
        Signal the vPoller Proxy process to shutdown

        """
        self.time_to_die.set()

    def distribute_tasks(self):
        """
        Distributes tasks from clients to workers for processing

        """
        socks = dict(self.zpoller.poll(1000))

        # Forward task from frontend to backend socket
        if socks.get(self.frontend) == zmq.POLLIN:
            logger.debug('Message received on frontend socket')
            task = self.frontend.recv()
            more = self.frontend.getsockopt(zmq.RCVMORE)
            if more:
                self.backend.send(task, zmq.SNDMORE)
            else:
                self.backend.send(task)
            logger.debug(
                'Sending message to backend socket: %s',
                task
            )

        # Forward result from backend to frontend socket
        if socks.get(self.backend) == zmq.POLLIN:
            logger.debug('Message received on backend socket')
            result = self.backend.recv()
            more = self.backend.getsockopt(zmq.RCVMORE)
            if more:
                self.frontend.send(result, zmq.SNDMORE)
            else:
                self.frontend.send(result)
            logger.debug(
                'Sending message to frontend socket: %s',
                result
            )

    def create_sockets(self):
        """
        Creates the ZeroMQ sockets used by the vPoller Proxy process

        """
        logger.info('Creating Proxy process sockets')
        
        self.zcontext = zmq.Context()
        self.frontend = self.zcontext.socket(zmq.ROUTER)
        self.backend = self.zcontext.socket(zmq.DEALER)
        self.frontend.bind(self.config.get('frontend'))
        self.backend.bind(self.config.get('backend'))
        self.zpoller = zmq.Poller()
        self.zpoller.register(self.frontend, zmq.POLLIN)
        self.zpoller.register(self.backend, zmq.POLLIN)

    def close_sockets(self):
        """
        Closes the ZeroMQ sockets used by vPoller Proxy process

        """
        logger.info('Closing Proxy process sockets')

        self.zpoller.unregister(self.frontend)
        self.zpoller.unregister(self.backend)
        self.frontend.close()
        self.backend.close()
        self.zcontext.term()
