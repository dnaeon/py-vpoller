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
vPoller Worker module

"""

import json
import importlib
import multiprocessing

from platform import node

try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser

import zmq

from vpoller import __version__
from vpoller.log import logger
from vpoller.client import validate_message
from vpoller.exceptions import VPollerException
from vpoller.task.registry import registry
from vconnector.core import VConnector
from vconnector.core import VConnectorDatabase

__all__ = ['VPollerWorkerManager', 'VPollerWorker']


class VPollerWorkerManager(object):
    """
    Manager of vPoller Workers

    """
    def __init__(self, config_file, num_workers=0):
        """
        Initializes a new vPoller Worker Manager

        Args:
            config_file (str): Path to the vPoller configuration file
            num_workers (str): Number of vPoller Worker 
                               processes to create

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
            'helpers': None,
            'tasks': None,
            'cache_maxsize': 0,
            'cache_enabled': False,
            'cache_ttl': 3600,
            'cache_housekeeping': 480,
        }

    def start(self):
        """
        Start the vPoller Worker Manager and processes

        """
        logger.info('Starting Worker Manager [%s release]', __version__)

        self.load_config()
        self.create_sockets()
        self.start_workers()

        logger.info('Worker Manager is ready and running')
        while not self.time_to_die.is_set():
            try:
                self.wait_for_mgmt_task()
            except KeyboardInterrupt:
                self.signal_stop()

        self.stop()

    def stop(self):
        """
        Stop the vPoller Manager and Workers

        """
        logger.info('Worker Manager is shutting down')
        self.close_sockets()
        self.stop_workers()

    def signal_stop(self):
        """
        Signal the vPoller Worker Manager that shutdown time has arrived

        """
        logger.info('Received shutdown signal')
        self.time_to_die.set()

        return {'success': 0, 'msg': 'Shutdown time has arrived'}

    def load_config(self):
        """
        Loads the vPoller Worker Manager configuration settings

        """
        logger.debug('Loading config file %s', self.config_file)

        parser = ConfigParser(self.config_defaults)
        parser.read(self.config_file)

        self.config['mgmt'] = parser.get('worker', 'mgmt')
        self.config['db'] = parser.get('worker', 'db')
        self.config['proxy'] = parser.get('worker', 'proxy')
        self.config['helpers'] = parser.get('worker', 'helpers')
        self.config['tasks'] = parser.get('worker', 'tasks')
        self.config['cache_enabled'] = parser.getboolean('cache', 'enabled')
        self.config['cache_maxsize'] = parser.getint('cache', 'maxsize')
        self.config['cache_ttl'] = parser.getint('cache', 'ttl')
        self.config['cache_housekeeping'] = parser.getint('cache', 'housekeeping')

        if self.config['helpers']:
            self.config['helpers'] = self.config['helpers'].split(',')

        if self.config['tasks']:
            self.config['tasks'] = self.config['tasks'].split(',')
        
        logger.debug(
            'Worker Manager configuration: %s',
            self.config
        )
        
    def start_workers(self):
        """
        Start the vPoller Worker processes

        """
        logger.info('Starting Worker processes')

        if self.num_workers <= 0:
            self.num_workers = multiprocessing.cpu_count()

        logger.info(
            'Concurrency: %d (processes)',
            self.num_workers
        )

        for i in range(self.num_workers):
            worker = VPollerWorker(
                db=self.config.get('db'),
                proxy=self.config.get('proxy'),
                helpers=self.config.get('helpers'),
                tasks=self.config.get('tasks'),
                cache_enabled=self.config.get('cache_enabled'),
                cache_maxsize=self.config.get('cache_maxsize'),
                cache_ttl=self.config.get('cache_ttl'),
                cache_housekeeping=self.config.get('cache_housekeeping')
            )
            worker.daemon = True
            self.workers.append(worker)
            worker.start()

    def stop_workers(self):
        """
        Stop the vPoller Worker processes

        """
        logger.info('Stopping Worker processes')

        for worker in self.workers:
            worker.signal_stop()
            worker.join(3)

    def create_sockets(self):
        """
        Creates the ZeroMQ sockets used by the vPoller Worker Manager

        """
        logger.debug('Creating Worker Manager sockets')

        self.zcontext = zmq.Context()
        self.mgmt_socket = self.zcontext.socket(zmq.REP)
        self.mgmt_socket.bind(self.config.get('mgmt'))
        self.zpoller = zmq.Poller()
        self.zpoller.register(self.mgmt_socket, zmq.POLLIN)

    def close_sockets(self):
        """
        Closes the ZeroMQ sockets used by the Manager

        """
        logger.debug('Closing Worker Manager sockets')

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
                    'Invalid message received on management interface',
                )
                self.mgmt_socket.send('Invalid message received')
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
        logger.debug('Processing management message: %s', msg)

        if 'method' not in msg:
            return {'success': 1, 'msg': 'Missing method name'}

        if msg['method'] not in self.mgmt_methods:
            return {'success': 1, 'msg': 'Unknown method name received'}

        method = msg['method']
        result = self.mgmt_methods[method]()

        return result

    def status(self):
        """
        Get status information about the vPoller Worker

        """
        logger.debug('Getting Worker status')

        result = {
            'success': 0,
            'msg': 'vPoller Worker status',
            'result': {
                'status': 'running',
                'hostname': self.node,
                'proxy': self.config.get('proxy'),
                'mgmt': self.config.get('mgmt'),
                'db': self.config.get('db'),
                'concurrency': self.num_workers,
                'helpers': self.config.get('helpers'),
                'tasks': self.config.get('tasks'),
            }
        }

        logger.debug('Returning result to client: %s', result)

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
    def __init__(self,
                 db,
                 proxy,
                 helpers,
                 tasks,
                 cache_enabled,
                 cache_maxsize,
                 cache_ttl,
                 cache_housekeeping,
    ):
        """
        Initialize a new VPollerWorker object

        Args:
            db                (str): Path to the vConnector database file
            proxy             (str): Endpoint to which vPoller Workers connect
                                     and receive new tasks for processing
            helpers           (list): A list of helper modules to be loaded
            task              (list): A list of task modules to be loaded
            cache_enabled     (bool): If True use an expiring cache for the
                                      managed objects
            cache_maxsize      (int): Upperbound limit on the number of items
                                      that will be stored in the cache
            cache_ttl          (int): Time in seconds after which a cached
                                      object is considered as expired
            cache_housekeeping (int): Time in minutes to perform
                                      periodic housekeeping of the cache

        """
        super(VPollerWorker, self).__init__()
        self.config = {
            'db': db,
            'proxy': proxy,
            'helpers': helpers,
            'tasks': tasks,
            'cache_enabled': cache_enabled,
            'cache_maxsize': cache_maxsize,
            'cache_ttl': cache_ttl,
            'cache_housekeeping': cache_housekeeping,
        }
        self.task_modules = {}
        self.helper_modules = {}
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
        logger.info('Worker process is starting')

        self.load_task_modules()
        self.load_helper_modules()
        self.create_sockets()
        self.create_agents()

        logger.info('Worker process is ready and running')
        while not self.time_to_die.is_set():
            try:
                self.wait_for_tasks()
            except KeyboardInterrupt:
                self.signal_stop()

        self.stop()

    def stop(self):
        """
        Stop vPoller Worker process

        """
        logger.info('Worker process is shutting down')
        self.close_sockets()
        self.stop_agents()

    def signal_stop(self):
        """
        Signal the vPoller Worker process that shutdown time has arrived

        """
        self.time_to_die.set()

    def load_task_modules(self):
        """
        Loads the task modules

        """
        if not self.config.get('tasks'):
            raise VPollerException('No task modules provided')

        for task in self.config.get('tasks'):
            task = task.strip()
            logger.info('Loading task module %s', task)
            try:
                module = importlib.import_module(task)
            except ImportError as e:
                logger.warning(
                    'Cannot import task module: %s',
                    e.message
                )
                continue
            self.task_modules[task] = module

        if not self.task_modules:
            raise VPollerException('No task modules loaded')

    def load_helper_modules(self):
        """
        Loads helper modules for post-processing of results

        """
        if not self.config.get('helpers'):
            return

        for helper in self.config.get('helpers'):
            helper = helper.strip()
            logger.info('Loading helper module %s', helper)
            try:
                module = importlib.import_module(helper)
            except ImportError as e:
                logger.warning(
                    'Cannot import helper module: %s',
                    e
                )
                continue

            if not hasattr(module, 'HelperAgent'):
                logger.warning(
                    'Module %s does not provide a HelperAgent interface',
                    helper
                )
                continue

            if not hasattr(module.HelperAgent, 'run'):
                logger.warning(
                    'In module %s HelperAgent class does not provide a run() method',
                    helper
                )
                continue

            self.helper_modules[helper] = module

    def run_helper(self, helper, msg, data):
        """
        Run a helper to post-process result data

        Args:
            helper (str): Name of the helper to run
            msg   (dict): The original message request
            data  (dict): The data to be processed

        """
        logger.debug(
            'Invoking helper module %s for processing of data',
            helper
        )

        module = self.helper_modules[helper]
        h = module.HelperAgent(msg=msg, data=data)

        try:
            result = h.run()
        except Exception as e:
            logger.warning('Helper module raised an exception: %s', e)
            return data

        return result

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
            _id = self.worker_socket.recv()
            _empty = self.worker_socket.recv()

            try:
                msg = self.worker_socket.recv_json()
            except Exception as e:
                logger.warning(
                    'Invalid client message received, will be ignored',
                )
                self.worker_socket.send(_id, zmq.SNDMORE)
                self.worker_socket.send(_empty, zmq.SNDMORE)
                self.worker_socket.send_json(
                    {'success': 1, 'msg': 'Invalid message received'}
                )
                return

            # Process task and return result to client
            result = self.process_client_msg(msg)
            
            # Process data using a helper before sending it to client?
            if 'helper' in msg and msg['helper'] in self.helper_modules:
                data = self.run_helper(
                    helper=msg['helper'],
                    msg=msg,
                    data=result
                )
            else:
                # No helper specified, dump data to JSON
                try:
                    data = json.dumps(result, ensure_ascii=False)
                except ValueError as e:
                    logger.warning('Cannot serialize result: %s', e)
                    r = {
                        'success': 1,
                        'msg': 'Cannot serialize result: %s' % e
                    }
                    data = json.dumps(r)

            # Send data to client
            self.worker_socket.send(_id, zmq.SNDMORE)
            self.worker_socket.send(_empty, zmq.SNDMORE)
            try:
                self.worker_socket.send_unicode(data)
            except TypeError as e:
                logger.warning('Cannot send result: %s', e)
                r = {'success': 1, 'msg': 'Cannot send result: %s' % e}
                self.worker_socket.send_unicode(json.dumps(r))

    def create_sockets(self):
        """
        Creates the ZeroMQ sockets used by the vPoller Worker

        Creates two sockets:

        """
        logger.info('Creating Worker sockets')

        self.zcontext = zmq.Context()
        self.worker_socket = self.zcontext.socket(zmq.DEALER)
        self.worker_socket.connect(self.config.get('proxy'))
        self.zpoller = zmq.Poller()
        self.zpoller.register(self.worker_socket, zmq.POLLIN)

    def close_sockets(self):
        """
        Closes the ZeroMQ sockets used by the vPoller Worker

        """
        logger.info('Closing Worker process sockets')
        
        self.zpoller.unregister(self.worker_socket)
        self.worker_socket.close()
        self.zcontext.term()

    def create_agents(self):
        """
        Prepares the vSphere Agents used by the vPoller Worker

        Raises:
            VPollerException

        """
        logger.debug('Creating vSphere Agents')

        db = VConnectorDatabase(self.config.get('db'))
        agents = db.get_agents(only_enabled=True)

        if not agents:
            logger.warning('No registered or enabled vSphere Agents found')
            raise VPollerException(
                'No registered or enabled vSphere Agents found'
            )

        for agent in agents:
            a = VConnector(
                user=agent['user'],
                pwd=agent['pwd'],
                host=agent['host'],
                cache_enabled=self.config.get('cache_enabled'),
                cache_maxsize=self.config.get('cache_maxsize'),
                cache_ttl=self.config.get('cache_ttl'),
                cache_housekeeping=self.config.get('cache_housekeeping')
            )
            self.agents[a.host] = a
            logger.info('Created vSphere Agent for %s', agent['host'])

    def stop_agents(self):
        """
        Disconnects all vPoller Agents

        """
        logger.debug('Shutting down vSphere Agents')

        for agent in self.agents:
            self.agents[agent].disconnect()

    def process_client_msg(self, msg):
        """
        Processes a client message received on the vPoller Worker socket

        The message is passed to the VSphereAgent object of the
        respective vSphere host in order to do the actual polling.

        Args:
            msg (dict): Client message for processing

        An example message for discovering the hosts could be:

            {
                "method":   "host.discover",
                "hostname": "vc01.example.org",
            }

        An example message for polling a datastore property could be:

            {
                "method":   "datastore.poll",
                "hostname": "vc01.example.org",
                "info.url": "ds:///vmfs/volumes/5190e2a7-d2b7c58e-b1e2/",
                "property": "summary.capacity"
            }

        """
        logger.debug('Processing client message: %s', msg)

        if not isinstance(msg, dict):
            return {
                'success': 1,
                'msg': 'Expected a JSON message, received {}'.format(msg.__class__)
            }

        task = registry.get(msg.get('method'))
        agent = self.agents.get(msg.get('hostname'))

        if not task:
            return {'success': 1, 'msg': 'Unknown or missing task/method name'}

        if not agent:
            return {'success': 1, 'msg': 'Unknown or missing agent name'}

        if not validate_message(msg=msg, required=task.required):
            return {'success': 1, 'msg': 'Invalid task request'}

        result = task.function(agent, msg)

        return result
