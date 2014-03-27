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
vPoller Connector Module

This module provides classes and methods for managing 
connections to VMware vSphere hosts and retrieve objects

"""

import logging

from pyVim.connect import SmartConnect, Disconnect

class VConnectorException(Exception):
    """
    Generic VConnector exception

    """
    pass

class VConnector(object):
    """
    VConnector class

    The VConnector class defines methods for connecting, disconnecting and
    retrieving objects from a VMware vSphere host

    Returns:
        VConnector object
    
    Raises:
        VConnectorException

    """
    def __init__(self, user, pwd, host):
        """
        Initializes a new VConnector object

        Args:
            user     (str): Username to use when connecting
            pwd      (str): Password to use when connecting 
            host     (str): VMware vSphere host to connect to

        """
        self.user = user
        self.pwd  = pwd
        self.host = host

    def connect(self):
        """
        Connect to the VMware vSphere host

        Raises:
             VPollerException
        
        """
        logging.info('Connecting to %s', self.host)
        
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
        logging.info('Disconnecting from %s', self.host)
        Disxconnect(self.si)

    def reconnect(self):
        """
        Reconnect to the VMware vSphere host

        """
        self.disconnect()
        self.connect()

    def get_all_datacenters(self):
        """
        Get a list of all pyVmomi.vim.Datacenter managed objects

        """
        obj_type = pyVmomi.vim.Datacenter
        logging.debug('Getting all %s managed objects', obj_type.__name__)
        return self._get_all_objects(obj_type=[obj_type])

    def get_all_clusters(self):
        """
        Get a list of all pyVmomi.vim.ClusterComputeResource managed objects

        """
        obj_type = pyVmomi.vim.ClusterComputeResource
        logging.debug('Getting all %s managed objects', obj_type.__name__)
        return self._get_all_objects(obj_type=[obj_type])

    def get_all_hosts(self):
        """
        Get a list of a ll pyVmomi.vim.HostSystem managed objects

        """
        obj_type = pyVmomi.vim.HostSystem
        logging.debug('Getting all %s managed objects', obj_type.__name__)
        return self._get_all_objects(obj_type=[obj_type])

    def get_all_vms(self):
        """
        Get a list of all pyVmomi.vim.VirtualMachine managed objects

        """
        obj_type = pyVmomi.vim.VirtualMachine
        logging.debug('Getting all %s managed objects', obj_type.__name__)
        return self._get_all_objects(obj_type=[obj_type])

    def get_all_datastores(self):
        """
        Get a list of all pyVmomi.vim.Datastore managed objects

        """
        obj_type = pyVmomi.vim.Datastore
        logging.debug('Getting all %s managed objects', obj_type.__name__)
        return self._get_all_objects(obj_type=[obj_type])

    def get_all_resource_pools(self):
        """
        Get a list of all pyVmomi.vim.ResourcePool managed objects

        """
        obj_type = pyVmomi.vim.ResourcePool
        logging.debug('Getting all %s managed objects', obj_type.__name__)
        return self._get_all_objects(obj_type=[obj_type])

    def _get_all_objects(self, obj_type):
        """
        Get all managed objects of type 'obj_type'

        Args:
            obj_type (list): A list of managed object types

        Returns:
            A list of managed objects
        
        """
        view_ref = self.si.content.viewManager.CreateContainerView(
            container=self.si.content.rootFolder,
            type=obj_type,
            recursive=True
        )

        result = view_ref.view
        view_ref.DestroyView()

        return result

