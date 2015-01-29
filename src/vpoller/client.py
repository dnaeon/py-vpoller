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
vPoller Client module for the VMware vSphere Poller

"""

import json

import zmq

from vpoller.log import logger

__all__ = ['VPollerClient', 'validate_message']


class VPollerClient(object):
    """
    VPollerClient class

    Defines methods used by clients for sending out message requests

    Sends out messages to a vPoller Proxy or vPoller Worker requesting
    properties of different vSphere objects, e.g. datastores, hosts, etc.

    Returns:
        The result message back to the client

    """
    def __init__(self, endpoint, timeout=3000, retries=3):
        """
        Initializes a VPollerClient object

        Args:
            timeout  (int): Timeout after that number of milliseconds
            retries  (int): Number of retries
            endpoint (str): Endpoint we connect the client to

        """
        self.timeout = timeout
        self.retries = retries
        self.endpoint = endpoint

    def run(self, msg):
        """
        Main vPoller Client method

        Partially based on the Lazy Pirate Pattern:

        http://zguide.zeromq.org/py:all#Client-Side-Reliability-Lazy-Pirate-Pattern

        Args:
            msg (dict): The client message to send

        """
        logger.debug('Endpoint to connect to: %s', self.endpoint)
        logger.debug('Timeout of request: %s ms', self.timeout)
        logger.debug('Number of retries: %d', self.retries)
        logger.debug('Message to be sent: %s', msg)

        self.zcontext = zmq.Context()
        self.zclient = self.zcontext.socket(zmq.REQ)
        self.zclient.connect(self.endpoint)
        self.zclient.setsockopt(zmq.LINGER, 0)
        self.zpoller = zmq.Poller()
        self.zpoller.register(self.zclient, zmq.POLLIN)
        result = None

        while self.retries > 0:
            logger.debug('Sending client message...')

            # Send our message out
            self.zclient.send_json(msg)
            socks = dict(self.zpoller.poll(self.timeout))

            # Do we have a reply?
            if socks.get(self.zclient) == zmq.POLLIN:
                logger.debug('Received response on client socket')
                result = self.zclient.recv_unicode()
                logger.debug('Received message was: %s', result)
                break
            else:
                # We didn't get a reply back from the server, let's retry
                self.retries -= 1
                logger.warning(
                    'Did not receive response, retrying...'
                )

                # Socket is confused. Close and remove it.
                logger.debug('Closing sockets and re-establishing connection...')
                self.zclient.close()
                self.zpoller.unregister(self.zclient)

                # Re-establish the connection
                logger.debug(
                    'Re-establishing connection to endpoint: %s',
                    self.endpoint
                )
                self.zclient = self.zcontext.socket(zmq.REQ)
                self.zclient.connect(self.endpoint)
                self.zclient.setsockopt(zmq.LINGER, 0)
                self.zpoller.register(self.zclient, zmq.POLLIN)

        # Close the socket and terminate the context
        logger.debug('Closing sockets and exiting')
        self.zclient.close()
        self.zpoller.unregister(self.zclient)
        self.zcontext.term()

        # Did we have any result reply at all?
        if result is None:
            logger.error(
                'Did not receive response, aborting...'
            )
            r = {
                'success': 1,
                'msg': 'Did not receive response, aborting...'
            }
            return json.dumps(r, ensure_ascii=False)

        return result


def validate_message(msg, required):
    """
    Helper method for validating a client message

    Returns:
        bool: True if message has been successfully validated

    """
    if not required:
        return True

    logger.debug(
        'Validating client message, required to have: %s',
        required
    )

    # Check if we have the required message attributes
    if not all(k in msg for k in required):
        logger.debug('Required message keys are missing')
        return False

    logger.debug('Client message successfully validated')

    return True
