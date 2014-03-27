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
The vconnector module provides classes and methods for establishing a 
connection to VMware vSphere hosts and retrieving objects.

"""

import logging

from pyVim.connect import SmartConnect, Disconnect

class VConnectorException(Exception):
    """
    Generic VConnector exception.

    """
    pass

class VConnector(object):
    """
    VConnector class.

    The VConnector class defines methods for connecting, disconnecting and
    retrieving objects from a VMware vSphere server instance.

    Returns:
        VConnector object
    
    Raises:
        VConnectorException

    """
    def __init__(self, user, pwd, host):
        """
        Initializes a new VConnector object.

        Args:
            user     (str): vSphere host
            pwd      (str): Username 
            host     (str): Password 

        """
        self.user = user
        self.pwd = pwd
        self.host = host

    def connect(self):
        """
        Connect to the VMware vSphere host

        Raises:
             VPollerException
        
        """
        logging.info('Connecting to vSphere host %s', self.host)
        
        try:
            self.si = SmartConnect(
                host=self.host,
                user=self.user,
                pwd=self.pwd
            )
        except Exception as e:
            raise VConnectorException, 'Cannot connect to %s: %s' % (self.host, e)
        
    def disconnect(self):
        """
        Disconnect from the VMware vSphere host

        """
        logging.info('Disconnecting from vSphere host %s', self.host)
        Disxconnect(self.si)

    def reconnect(self):
        """
        Reconnect to the VMware vSphere host

        """
        self.disconnect()
        self.connect()

