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
vPoller Agent module for the VMware vSphere Poller

vPoller Agents are used by the vPoller Workers, which take care of
establishing the connection to the vSphere hosts and do all the heavy lifting.

Check the vSphere Web Services SDK API for more information on the properties
you can request for any specific vSphere managed object

    - https://www.vmware.com/support/developer/vc-sdk/

"""

import logging

import zmq
import pyVmomi
from vpoller.core import VPollerException
from vpoller.connector import VConnector

class VSphereAgent(VConnector):
    """
    VSphereAgent class

    Defines methods for retrieving vSphere object properties

    These are the worker agents that do the actual polling from the vSphere host

    Extends:
        VConnector

    """
    def _discover_objects(self, properties, obj_type):
        """
        Helper method to simplify discovery of vSphere managed objects

        Args:
            properties          (list): List of properties to be collected
            obj_type   (pyVmomi.vim.*): Type of vSphere managed object

        Returns:
            The discovered objects in JSON format

        """
        logging.info('[%s] Discovering %s managed objects', obj_type.__name__)

        view_ref = self._get_object_view(obj_type=[obj_type])
        try:
            data = self.collect_properties(
                view_ref=view_ref,
                obj_type=obj_type,
                path_set=properties
            )
        except Exception as e:
            return { 'success': -1, 'msg': 'Cannot discover objects: %s' % e }

        result = {
            'success': 0,
            'msg': 'Successfully discovered objects',
            'result': data,
        }

        logging.debug('Returning result from discovery: %s', result)

        return result

    def datacenter_discover(self, msg):
        """
        Discover all pyVmomi.vim.Datacenter managed objects

        Example client message would be:
        
            {
                "method":   "datacenter.discover",
        	"hostname": "vc01.example.org",
            }

        Example client message which also requests additional properties:

            {
                "method":     "datacenter.discover",
                "hostname":   "vc01.example.org",
                "properties": [
                    "name",
                    "overallStatus"
                ]
            }
        
        Returns:
            The discovered objects in JSON format

        """
        # Property names to be collected
        properties = ['name']
        if msg.has_key('properties') and msg['properties']:
            properties.extend(msg['properties'])

        return self._discover_objects(properties=properties, obj_type=pyVmomi.vim.Datacenter)

    def cluster_discover(self, msg):
        """
        Discover all pyVmomi.vim.ClusterComputeResource managed objects

        Example client message would be:
        
            {
                "method":   "cluster.discover",
        	"hostname": "vc01.example.org",
            }

        Example client message which also requests additional properties:

            {
                "method":     "cluster.discover",
                "hostname":   "vc01.example.org",
                "properties": [
                    "name",
                    "overallStatus"
                ]
            }
              
        Returns:
            The discovered objects in JSON format

        """
        # Property names to be collected
        properties = ['name']
        if msg.has_key('properties') and msg['properties']:
            properties.extend(msg['properties'])
            
        return self._discover_objects(properties=properties, obj_type=pyVmomi.vim.ClusterComputeResource)

    def resource_pool_discover(self, msg):
        """
        Discover all pyVmomi.vim.ResourcePool managed objects

        Example client message would be:
        
            {
                "method":   "resource.pool.discover",
        	"hostname": "vc01.example.org",
            }

        Example client message which also requests additional properties:

            {
                "method":     "resource.pool.discover",
                "hostname":   "vc01.example.org",
                "properties": [
                    "name",
                    "overallStatus"
                ]
            }
              
        Returns:
            The discovered objects in JSON format

        """
        # Property names to be collected
        properties = ['name']
        if msg.has_key('properties') and msg['properties']:
            properties.extend(msg['properties'])
            
        return self._discover_objects(properties=properties, obj_type=pyVmomi.vim.ResourcePool)
    
    def host_discover(self, msg):
        """
        Discover all pyVmomi.vim.HostSystem managed objects

        Example client message would be:
        
            {
                "method":   "host.discover",
        	"hostname": "vc01.example.org",
            }

        Example client message which also requests additional properties:

            {
                "method":     "host.discover",
                "hostname":   "vc01.example.org",
                "properties": [
                    "name",
                    "runtime.powerState"
                ]
            }
              
        Returns:
            The discovered objects in JSON format

        """
        # Property names to be collected
        properties = ['name']
        if msg.has_key('properties') and msg['properties']:
            properties.extend(msg['properties'])

        return self._discover_objects(properties=properties, obj_type=pyVmomi.vim.HostSystem)

    def vm_discover(self, msg):
        """
        Discover all pyVmomi.vim.VirtualMachine managed objects

        Example client message would be:
        
            {
                "method":   "vm.discover",
        	"hostname": "vc01.example.org",
            }

        Example client message which also requests additional properties:

            {
                "method":     "vm.discover",
                "hostname":   "vc01.example.org",
                "properties": [
                    "name",
                    "runtime.powerState"
                ]
            }
              
        Returns:
            The discovered objects in JSON format

        """
        # Property names to be collected
        properties = ['name']
        if msg.has_key('properties') and msg['properties']:
            properties.extend(msg['properties'])

        return self._discover_objects(properties=properties, obj_type=pyVmomi.vim.VirtualMachine)

    def datastore_discover(self, msg):
        """
        Discover all pyVmomi.vim.Datastore managed objects

        Example client message would be:
        
            {
                "method":   "datastore.discover",
        	"hostname": "vc01.example.org",
            }

        Example client message which also requests additional properties:

            {
                "method":     "datastore.discover",
                "hostname":   "vc01.example.org",
                "properties": [
                    "name",
                    "summary.url"
                ]
            }
              
        Returns:
            The discovered objects in JSON format

        """
        # Property names to be collected
        properties = ['name']
        if msg.has_key('properties') and msg['properties']:
            properties.extend(msg['properties'])

        return self._discover_objects(properties=properties, obj_type=pyVmomi.vim.Datastore)
