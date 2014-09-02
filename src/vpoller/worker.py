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

import logging
import multiprocessing
from platform import node
from ConfigParser import ConfigParser

import zmq
from vpoller.core import VPollerException
from vpoller.agent import VSphereAgent
from vconnector.core import VConnectorDatabase

class VPollerWorkerManager(object):
    """
    Manager of vPoller Workers

    """
    def __init__(self, config_file, num_workers=0):
        """
        Initializes a new vPoller Worker Manager

        Args:
            config_file (str): Path to the vPoller configuration file
            num_workers (str): Number of vPoller Worker processes to create

        """
        self.node = node()
        self.config_file = config_file
        self.num_workers = num_workers
        self.time_to_die = multiprocessing.Event()
        self.config = {}
        self.workers = []
        self.zcontext = None
        self.zpoller = None
        self.mgmt_socket = None
        self.mgmt_methods = {
            'status': self.status,
            'shutdown': self.signal_stop,
        }
        self.config_defaults = {
            'db': '/var/lib/vconnector/vconnector.db',
            'mgmt': 'tcp://*:10000',
            'proxy': 'tcp://localhost:10123',
        }

    def start(self):
        """
        Start the vPoller Worker Manager and processes

        """
        logging.info('Starting vPoller Worker Manager')

        self.load_config()
        self.create_sockets()
        self.start_workers()

        while not self.time_to_die.is_set():
            self.wait_for_mgmt_task()

        self.stop()

    def stop(self):
        """
        Stop the vPoller Manager and Workers

        """
        self.close_sockets()
        self.stop_workers()

    def signal_stop(self):
        """
        Signal the vPoller Worker Manager that shutdown time has arrived

        """
        self.time_to_die.set()

        return { 'success': 0, 'msg': 'Shutdown time has arrived' }

    def load_config(self):
        """
        Loads the vPoller Worker Manager configuration settings

        """
        logging.debug('Loading config file %s', self.config_file)

        parser = ConfigParser(self.config_defaults)
        parser.read(self.config_file)

        self.config['mgmt'] = parser.get('worker', 'mgmt')
        self.config['db'] = parser.get('worker', 'db')
        self.config['proxy'] = parser.get('worker', 'proxy')
        
    def start_workers(self):
        """
        Start the vPoller Worker processes

        """
        logging.info('Starting vPoller Worker processes')
        
        if self.num_workers <= 0:
            self.num_workers = multiprocessing.cpu_count()

        for i in xrange(self.num_workers):
            worker = VPollerWorker(
                db=self.config.get('db'),
                proxy=self.config.get('proxy')
            )
            worker.daemon = True
            self.workers.append(worker)
            worker.start()

    def stop_workers(self):
        """
        Stop the vPoller Worker processes

        """
        logging.info('Stopping vPoller Worker processes')
        
        for worker in self.workers:
           worker.signal_stop()
           worker.join(3)

    def create_sockets(self):
        """
        Creates the ZeroMQ sockets used by the vPoller Worker Manager

        """
        logging.debug('Creating vPoller Worker Manager sockets')

        self.zcontext = zmq.Context()
        self.mgmt_socket = self.zcontext.socket(zmq.REP)
        self.mgmt_socket.bind(self.config.get('mgmt'))
        self.zpoller = zmq.Poller()
        self.zpoller.register(self.mgmt_socket, zmq.POLLIN)

    def close_sockets(self):
        """
        Closes the ZeroMQ sockets used by the Manager

        """
        logging.debug('Closing vPoller Worker Manager sockets')
        
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
            return { 'success': 1, 'msg': 'Unknown method name received' }

        method = msg['method']
        result = self.mgmt_methods[method]()

        return result
 
    def status(self):
        """
        Get status information about the vPoller Worker
            
        """
        logging.debug('Getting vPoller Worker status')

        result = {
            'success': 0,
            'msg': 'vPoller Worker status',
            'result': {
                'status': 'running',
                'hostname': self.node,
                'proxy': self.config.get('proxy'),
                'mgmt': self.config.get('mgmt'),
                'db': self.config.get('db'),
                'concurrency': len(self.workers),
            }
        }

        logging.debug('Returning result to client: %s', result)

        return result
            
class VPollerWorker(multiprocessing.Process):
    """
    VPollerWorker class

    A vPoller Worker object runs the vSphere Agents, which are
    responsible for making vSphere API requests

    Extends:
        multiprocessing.Process

    Overrides:
        run() method

    """
    def __init__(self, db, proxy):
        """
        Initialize a new VPollerWorker object

        Args:
            db    (str): Path to the vConnector database file
            proxy (str): Endpoint from which the vPoller Worker receives new tasks

        """
        super(VPollerWorker, self).__init__()
        self.config = {
            'db': db,
            'proxy': proxy,
        }
        self.time_to_die = multiprocessing.Event()
        self.agents = {}
        self.zcontext = None
        self.zpoller = None
        self.worker_socket = None

    def run(self):
        """
        The main worker method.

        Args:
            config (str): Path to the confuguration file for vPoller Worker

        """
        logging.info('vPoller Worker process is starting')

        self.create_sockets()
        self.create_agents()

        while not self.time_to_die.is_set():
            self.wait_for_tasks()

        self.stop()

    def stop(self):
        """
        Stop vPoller Worker process

        """
        self.close_sockets()
        self.stop_agents()

    def signal_stop(self):
        """
        Signal the vPoller Worker process that shutdown time has arrived

        """
        self.time_to_die.set()
        
    def wait_for_tasks(self):
        """
        Poll the worker socket for new tasks

        """
        socks = dict(self.zpoller.poll(1000))

        # The routing envelope of the message on the worker socket is this:
        #
        # Frame 1: [ N ][...]  <- Identity of connection
        # Frame 2: [ 0 ][]     <- Empty delimiter frame
        # Frame 3: [ N ][...]  <- Data frame
        if socks.get(self.worker_socket) == zmq.POLLIN:
            # TODO: Use recv_multipart() 
            _id    = self.worker_socket.recv()
            _empty = self.worker_socket.recv()

            try:
                msg = self.worker_socket.recv_json()
            except Exception as e:
                logging.warning('Invalid client message received, will be ignored: %s', msg)

            # Process task and return result to client
            result = self.process_client_msg(msg)
            self.worker_socket.send(_id, zmq.SNDMORE)
            self.worker_socket.send("", zmq.SNDMORE)
            try:
                self.worker_socket.send_json(result)
            except TypeError as e:
                logging.warning('Cannot serialize result: %s', e)
                self.worker_socket.send_json({ 'success': 1, 'msg': 'Cannot serialize result: %s' % e})

    def create_sockets(self):
        """
        Creates the ZeroMQ sockets used by the vPoller Worker

        Creates two sockets: 

        """
        logging.debug('Creating vPoller Worker sockets')
        
        self.zcontext = zmq.Context()
        self.worker_socket = self.zcontext.socket(zmq.DEALER)
        self.worker_socket.connect(self.config.get('proxy'))
        self.zpoller = zmq.Poller()
        self.zpoller.register(self.worker_socket, zmq.POLLIN)

    def close_sockets(self):
        """
        Closes the ZeroMQ sockets used by the vPoller Worker

        """
        self.zpoller.unregister(self.worker_socket)
        self.worker_socket.close()
        self.zcontext.term()

    def create_agents(self):
        """
        Prepares the vSphere Agents used by the vPoller Worker

        Raises:
            VPollerException

        """
        logging.debug('Creating vSphere Agents')

        db = VConnectorDatabase(self.config.get('db'))
        agents = db.get_agents(only_enabled=True)

        if not agents:
            logging.warning('No registered or enabled vSphere Agents found')
            raise VPollerException, 'No registered or enabled vSphere Agents found'

        for agent in agents:
            a = VSphereAgent(
                user=agent['user'],
                pwd=agent['pwd'],
                host=agent['host']
            )
            self.agents[a.host] = a

    def stop_agents(self):
        """
        Disconnects all vPoller Agents from the VMware vSphere hosts they are connected to
        
        """
        logging.debug('Shutting down vSphere Agents')

        for agent in self.agents:
            self.agents[agent].disconnect()
        
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

        # Check whether the client message is a valid one
        if not isinstance(msg, dict):
            return { 'success': 1, 'msg': 'Expected a JSON message, received %s' % msg.__class__ }

        if not 'method' in msg:
            return { 'success': 1, 'msg': 'Missing method name' }

        # Get the vSphere Agent object for handling this request
        requested_method = msg.get('method')
        requested_agent = msg.get('hostname')
        agent = self.agents.get(requested_agent)

        if not agent:
            return { 'success': 1, 'msg': 'Unknown or missing vSphere Agent requested' }

        agent_method = agent.agent_methods.get(requested_method)
        
        if not agent_method:
            return { 'success': 1, 'msg': 'Unknown method name requested' }

        # Validate client message for required message attributes and type
        required = agent.agent_methods.get(requested_method)['required']
        if not agent._validate_client_msg(msg, required):
            return { 'success': 1, 'msg': 'Incorrect task request received' }
            
        result = agent_method['method'](msg)

        return result
