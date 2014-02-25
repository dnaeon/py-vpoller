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

"""

import types
import logging

import zmq
from vpoller.core import VPollerException
from vconnector.core import VConnector
from pysphere import MORTypes

class VSphereAgent(VConnector):
    """
    VSphereAgent class

    Defines methods for retrieving vSphere objects' properties.

    These are the worker agents that do the actual polling from the vSphere host.

    Extends:
        VConnector

    """
    def msg_is_okay(self, msg, attr):
        """
        Sanity checks the message for required attributes.

        Check for proper attribute type is also performed.
        
        Also checks whether the vSphere Agent is connected and
        if not, it will re-connect the Agent to the vSphere host.

        Args:
            msg   (dict): The client message
            attr (tuple): A tuple of the required message attributes
        
        Returns:
            True if the message contains all required properties, False otherwise.

        """
        # The message attributes types we accept
        msg_types = {
            'method':     (types.StringType, types.UnicodeType),
            'hostname':   (types.StringType, types.UnicodeType),
            'name':       (types.StringType, types.UnicodeType, types.NoneType),
            'properties': (types.TupleType,  types.ListType, types.NoneType),
            }
        
        if not all (k in msg for k in attr):
            return False

        for k in msg.keys():
            if not isinstance(msg[k], msg_types[k]):
                return False
        
        if not self.viserver.is_connected():
            self.reconnect()

        return True
    
    def get_host_property(self, msg):
        """
        Get property of an object of type HostSystem and return it.

        Example client message to get a host property could be:

            {
                "method":     "host.get",
                "hostname":   "vc01-test.example.org",
                "name":       "esxi01-test.example.org",
                "properties": [
                    "hardware.memorySize",
                    "runtime.bootTime"
                ]
            }
        
        Args:
            msg (dict): The client message to process

        """

        #
        # TODO: Handle collection objects as part of the returned result
        # 
        
        if not self.msg_is_okay(msg, ('method', 'hostname', 'name', 'properties')):
            return { "success": -1, "msg": "Incorrect or missing message properties" }

        #
        # Property names we want to retrieve about the HostSystem object plus
        # any other user-requested properties.
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['name']
        property_names.extend(msg['properties'])

        logging.info('[%s] Retrieving %s for host %s', self.hostname, msg['properties'], msg['name'])

        self.update_host_mors()
        mor = self.mors_cache['HostSystem']['objects'].get(msg['name'])

        if not mor:
            return { "success": -1, "msg": "Unable to find ESXi host %s" % msg['name'] }

        # Get the properties 
        try:
            result = self.viserver._get_object_properties(mor=mor, property_names=property_names)
        except Exception as e:
	    logging.warning("Cannot get property for host %s: %s", msg['name'], e)
            return { "success": -1, "msg": "Cannot get property for host %s: %s" % (msg['name'], e) }

        ps = result.get_element_propSet()
        
        result = { "success": 0,
                   "msg": "Successfully retrieved properties",
                   "result": {p.Name:p.Val for p in ps},
                   }
        
        return result
            
    def get_datastore_property(self, msg):
        """
        Get property of an object of type Datastore and return it.

        Example client message to get a host property could be:

            {
                "method":     "datastore.get",
                "hostname":   "vc01-test.example.org",
                "name":       "ds:///vmfs/volumes/5190e2a7-d2b7c58e-b1e2-90b11c29079d/",
                "properties": [
                    "summary.capacity",
                    "info.freeSpace",
                ]
            }
        
        Args:
            msg (dict): The client message to process
        
        """
        
        #
        # TODO: Handle collection objects as part of the returned result
        # 

        if not self.msg_is_okay(msg, ('method', 'hostname', 'name', 'properties')):
            return { "success": -1, "msg": "Incorrect or missing message properties" }

        #
        # Property names we want to retrieve about the Datastore object plus any
        # other user-requested properties.
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['info.url']
        property_names.extend(msg['properties'])

        logging.info('[%s] Retrieving %s for datastore %s', self.hostname, msg['properties'], msg['name'])

        self.update_datastore_mors()
        mor = self.mors_cache['Datastore']['objects'].get(msg['name'])

        if not mor:
            return { "success": -1, "msg": "Unable to find datastore %s" % msg['name'] }

        try:
            result = self.viserver._get_object_properties(mor=mor, property_names=property_names)
        except Exception as e:
            logging.warning("Cannot get property for datastore %s: %s" % (msg['name'], e))
            return { "success": -1, "msg": "Cannot get property for datastore %s: %s" % (msg['name'], e) }

        ps = result.get_element_propSet()

        result = { "success": 0,
                   "msg": "Successfully retrieved properties",
                   "result": {p.Name:p.Val for p in ps},
                   }

        return result

    def get_vm_property(self, msg):
        """
        Get property of an object of type VirtualMachine and return it.

        Example client message to get a VM property could be:

            {
                "method":     "vm.get",
                "hostname":   "vc01-test.example.org",
                "name":       "vm01.example.org",
                "properties": [
                    "config.uuid",
                    "config.guestFullName"
                ]
            }
        
        Args:
            msg (dict): The client message to process

        """

        #
        # TODO: Handle collection objects as part of the returned result
        # 

        if not self.msg_is_okay(msg, ('method', 'hostname', 'name', 'properties')):
            return { "success": -1, "msg": "Incorrect or missing message properties" }

        #
        # Property names we want to retrieve about the VirtualMachine object plus
        # any other user-requested properties.
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['config.name']
        property_names.extend(msg['properties'])

        logging.info('[%s] Retrieving %s for Virtual Machine %s', self.hostname, msg['properties'], msg['name'])

        self.update_vm_mors()
        mor = self.mors_cache['VirtualMachine']['objects'].get(msg['name'])

        if not mor:
            return { 'success': -1, 'msg': 'Unable to find Virtual Machine %s' % msg['name'] }

        try:
            result = self.viserver._get_object_properties(mor=mor, property_names=property_names)
        except Exception as e:
	    logging.warning('Cannot get property for Virtual Machine %s: %s', msg['name'], e)
            return { 'success': -1, 'msg': 'Cannot get property for Virtual Machine %s: %s' % (msg['name'], e) }

        ps = result.get_element_propSet()
        
        result = { "success": 0,
                   "msg": "Successfully retrieved properties",
                   "result": {p.Name:p.Val for p in ps},
                   }
        
        return result

    def _get_performance_manager(self):
        """
        One-time method to set the PerformanceManager attribute

        Useful for setting up the PerformanceManager once and avoid
        subsequent calls for acquiring a new PerformanceManager each time
        we need to query performance counters.

        """
        if hasattr(self, 'pm'):
            return

        self.pm = self.viserver.get_performance_manager()

    def get_vm_counter(self, msg):
        """
        Get performance counters of an object of type VirtualMachine and return it.

        Example client message to get a VM performance counter could be:

            {
                "method":     "vm.counter.get",
                "hostname":   "vc01-test.example.org",
                "name":       "vm01.example.org",
                "properties": [
                    "cpu.system",
                    "mem.zipped"
                ]
            }
        
        Args:
            msg (dict): The client message to process

        """

        #
        # TODO: Handle collection objects as part of the returned result
        # 

        if not self.msg_is_okay(msg, ('method', 'hostname', 'name', 'properties')):
            return { "success": -1, "msg": "Incorrect or missing message properties" }

        #
        # Performance Counter names we want to retrieve about the VirtualMachine object plus
        # any other user-requested properties.
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        counter_names = msg['properties']

        logging.info('[%s] Retrieving %s for Virtual Machine %s', self.hostname, msg['properties'], msg['name'])

        # Locate the VirtualMachine MOR for which we want to get the performance counters
        self.update_vm_mors()
        mor = self.mors_cache['VirtualMachine']['objects'].get(msg['name'])

        if not mor:
            return { 'success': -1, 'msg': 'Unable to find Virtual Machine %s' % msg['name'] }

        self._get_performance_manager()

        try:
            result = self.pm.get_entity_statistic(entity=mor, counters=counter_names)
        except Exception as e:
	    logging.warning('Cannot get counters for Virtual Machine %s: %s', msg['name'], e)
            return { 'success': -1, 'msg': 'Cannot get counters for Virtual Machine %s: %s' % (msg['name'], e) }

        data = []

        for eachCounter in result:
          data.append(
            { 'name': eachCounter.group + '.' + eachCounter.counter,
              'counter': eachCounter.counter,
              'group': eachCounter.group,
              'description': eachCounter.description,
              'unit': eachCounter.unit,
              'group_description': eachCounter.group_description,
              'unit_description': eachCounter.unit_description,
              'value': eachCounter.value
            }
          )

        result = {
            "success": 0,
            "msg": "Successfully retrieved counters",
            "result": data,
        }
        
        return result

    def get_vm_counter_all(self, msg):
        """
        Get all performance counters of an object of type VirtualMachine and return them.

        Example client message to get all VM performance counters could be:

            {
                "method":     "vm.counter.all",
                "hostname":   "vc01-test.example.org",
                "name":       "vm01.example.org",
            }
        
        Args:
            msg (dict): The client message to process

        """

        #
        # TODO: Handle collection objects as part of the returned result
        # 

        if not self.msg_is_okay(msg, ('method', 'hostname', 'name')):
            return { "success": -1, "msg": "Incorrect or missing message properties" }

        logging.info('[%s] Retrieving all performance counters for %s', self.hostname, msg['name'])

        # Locate the VirtualMachine MOR for which we want to get the performance counters
        self.update_vm_mors()
        mor = self.mors_cache['VirtualMachine']['objects'].get(msg['name'])

        if not mor:
            return { 'success': -1, 'msg': 'Unable to find Virtual Machine %s' % msg['name'] }

        self._get_performance_manager()

        try:
            data = self.pm.get_entity_counters(entity=mor)
        except Exception as e:
	    logging.warning('Cannot get counters for Virtual Machine %s: %s', msg['name'], e)
            return { 'success': -1, 'msg': 'Cannot get counters for Virtual Machine %s: %s' % (msg['name'], e) }

        result = {
            "success": 0,
            "msg": "Successfully retrieved counters",
            "result": data,
        }
        
        return result
    
    def get_datacenter_property(self, msg):
        """
        Get property of an object of type Datacenter and return it.

        Example client message to get a Datacenter property could be:

            {
                "method":     "datacenter.get",
                "hostname":   "vc01-test.example.org",
                "name":       "Dc01",
                "properties": [
                    "name"
                ]
            }
        
        Args:
            msg (dict): The client message to process

        """

        #
        # TODO: Handle collection objects as part of the returned result
        # 
        
        if not self.msg_is_okay(msg, ('method', 'hostname', 'name', 'properties')):
            return { "success": -1, "msg": "Incorrect or missing message properties" }

        #
        # Currently we don't support polling of Datacenter object properties as the
        # properties are mostly collections and we need a way to nicely process
        # collection objects before we enable this.
        #

        return { 'success': -1, 'msg': 'Polling of Datacenter properties is not implemented yet' }

    def get_cluster_property(self, msg):
        """
        Get property of an object of type ClusterComputeResource and return it.

        Example client message to get a cluster property could be:

            {
                "method":     "cluster.get",
                "hostname":   "vc01-test.example.org",
                "name":       "Cluster01",
                "properties": [
                    "configuration.drsConfig.enabled",
                ]
            }
        
        Args:
            msg (dict): The client message to process

        """

        #
        # TODO: Handle collection objects as part of the returned result
        # 
        
        if not self.msg_is_okay(msg, ('method', 'hostname', 'name', 'properties')):
            return { 'success': -1, 'msg': 'Incorrect or missing message properties' }

        #
        # Property names we want to retrieve about the ClusterComputeResource object plus
        # any other user-requested properties.
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['name']
        property_names.extend(msg['properties'])

        logging.info('[%s] Retrieving %s for cluster %s', self.hostname, msg['properties'], msg['name'])

        self.update_cluster_mors()
        mor = self.mors_cache['ClusterComputeResource']['objects'].get(msg['name'])

        if not mor:
            return { "success": -1, "msg": "Unable to find cluster %s" % msg['name'] }

        try:
            result = self.viserver._get_object_properties(mor=mor, property_names=property_names)
        except Exception as e:
	    logging.warning("Cannot get property for cluster %s: %s", msg['name'], e)
            return { "success": -1, "msg": "Cannot get property for cluster %s: %s" % (msg['name'], e) }

        ps = result.get_element_propSet()
        
        result = { "success": 0,
                   "msg": "Successfully retrieved properties",
                   "result": {p.Name:p.Val for p in ps},
                   }
        
        return result
    
    def discover_hosts(self, msg):
        """
        Discovers all ESXi hosts registered in the VMware vSphere server.

        Example client message to discover all ESXi hosts could be:

            {
                "method":   "host.discover",
                "hostname": "vc01-test.example.org",
            }

        Example client message which requests also additional properties:

            {
                "method":     "host.discover",
                "hostname":   "vc01-test.example.org",
                "properties": [
                    "hardware.memorySize",
                    "runtime.bootTime",
                ]
            }
              
        Returns:
            The returned data is a JSON object, containing the discovered ESXi hosts.

        """

        #
        # TODO: Handle collection objects as part of the returned result
        # 
        
        if not self.msg_is_okay(msg, ('method', 'hostname')):
            return { 'success': -1, 'msg': 'Incorrect or missing message properties' }
        
        # Properties we want to retrieve are 'name' and 'runtime.powerState'
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['name', 'runtime.powerState']

        if msg.has_key('properties') and msg['properties']:
            property_names.extend(msg['properties'])

        logging.info('[%s] Discovering ESXi hosts', self.hostname)

	try:
            result = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                                obj_type=MORTypes.HostSystem)
	except Exception as e:
            logging.warning("Cannot discover ESXi hosts: %s", e)
            return { "success": -1, "msg": "Cannot discover ESXi hosts: %s" % e }

        data = [{p.Name:p.Val for p in item.PropSet} for item in result]

        return { "success": 0,
                 "msg": "Successfully discovered ESXi hosts",
                 "result": data
                 }

    def discover_datastores(self, msg):
        """
        Discovers all datastores registered in a VMware vSphere server.

        Example client message to discover all datastores could be:
        
            {
                "method":   "datastore.discover",
        	"hostname": "vc01-test.example.org",
            }

        Example client message which requests also additional properties:

            {
                "method":     "datastore.discover",
                "hostname":   "vc01-test.example.org",
                "properties": [
                    "info.freeSpace"
                    "summary.capacity",
                ]
            }
              
        Returns:
            The returned data is a JSON object, containing the discovered datastores.

        """
        
        #
        # TODO: Handle collection objects as part of the returned result
        # 
        
        if not self.msg_is_okay(msg, ('method', 'hostname')):
            return { 'success': -1, 'msg': 'Incorrect or missing message properties' }
        
        # Properties we want to retrieve about the datastores plus any
        # other user-requested properties
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['info.name', 'info.url', 'summary.accessible']

        if msg.has_key('properties') and msg['properties']:
            property_names.extend(msg['properties'])
        
        logging.info('[%s] Discovering datastores', self.hostname)
        
	try:
            result = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                                   obj_type=MORTypes.Datastore)
	except Exception as e:
            logging.warning("Cannot discover datastores: %s", e)
            return { "success": -1, "msg": "Cannot discover datastores: %s" % e }

        data = [{p.Name:p.Val for p in item.PropSet} for item in result]

        return { "success": 0,
                 "msg": "Successfully discovered datastores",
                 "result": data,
                 }

    def discover_virtual_machines(self, msg):
        """
        Discovers all VirtualMachines registered in a VMware vSphere server.

        Example client message to discover all Virtual Machines could be:
        
            {
                "method":   "vm.discover",
        	"hostname": "vc01-test.example.org",
            }

        Example client message which requests also additional properties:

            {
                "method":     "vm.discover",
                "hostname":   "vc01-test.example.org",
                "properties": [
                    "summary.overallStatus"
                    "runtime.powerState",
                ]
            }
              
        Returns:
            The returned data is a JSON object, containing the discovered Virtual Machines.

        """
        #
        # TODO: Handle collection objects as part of the returned result
        # 
        
        if not self.msg_is_okay(msg, ('method', 'hostname')):
            return { 'success': -1, 'msg': 'Incorrect or missing message properties' }
        
        # Properties we want to retrieve about the Virtual Machines plus any
        # other user-requested properties
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['config.name', 'runtime.powerState']

        if msg.has_key('properties') and msg['properties']:
            property_names.extend(msg['properties'])
        
        logging.info('[%s] Discovering Virtual Machines', self.hostname)
        
	try:
            result = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                                  obj_type=MORTypes.VirtualMachine)
	except Exception as e:
            logging.warning("Cannot discover Virtual Machines: %s", e)
            return { "success": -1, "msg": "Cannot discover Virtual Machines: %s" % e }

        data = [{p.Name:p.Val for p in item.PropSet} for item in result]

        return { "success": 0,
                 "msg": "Successfully discovered Virtual Machines",
                 "result": data,
                 }
    
    def discover_datacenters(self, msg):
        """
        Discovers all Datacenters registered in a VMware vSphere server.

        Example client message to discover all Datacenters could be:
        
            {
                "method":   "datacenter.discover",
        	"hostname": "vc01-test.example.org",
            }

        Example client message which requests also additional properties:

            {
                "method":     "datacenter.discover",
                "hostname":   "vc01-test.example.org",
                "properties": [
                ]
            }
              
        Returns:
            The returned data is a JSON object, containing the discovered Datacenters.

        """

        #
        # TODO: Handle collection objects as part of the returned result
        # 
        
        if not self.msg_is_okay(msg, ('method', 'hostname')):
            return { 'success': -1, 'msg': 'Incorrect or missing message properties' }
        
        # Properties we want to retrieve about the Datacenters plus any
        # other user-requested properties
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['name']

        if msg.has_key('properties') and msg['properties']:
            property_names.extend(msg['properties'])
        
        logging.info('[%s] Discovering Datacenters', self.hostname)
        
	try:
            result = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                                  obj_type=MORTypes.Datacenter)
	except Exception as e:
            logging.warning("Cannot discover Datacenters: %s", e)
            return { "success": -1, "msg": "Cannot discover Datacenters: %s" % e }

        data = [{p.Name:p.Val for p in item.PropSet} for item in result]

        return { "success": 0,
                 "msg": "Successfully discovered Datacenters",
                 "result": data,
                 }
    
    def discover_clusters(self, msg):
        """
        Discovers all ClusterComputeResource objects in a VMware vSphere server.

        Example client message to discover all clusters could be:
        
            {
                "method":   "cluster.discover",
        	"hostname": "vc01-test.example.org",
            }

        Example client message which requests also additional properties:

            {
                "method":     "cluster.discover",
                "hostname":   "vc01-test.example.org",
                "properties": [
                ]
            }
              
        Returns:
            The returned data is a JSON object, containing the discovered Clusters.

        """

        #
        # TODO: Handle collection objects as part of the returned result
        # 
        
        if not self.msg_is_okay(msg, ('method', 'hostname')):
            return { 'success': -1, 'msg': 'Incorrect or missing message properties' }
        
        # Properties we want to retrieve about the ClusterComputeResource plus any
        # other user-requested properties
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['name']

        if msg.has_key('properties') and msg['properties']:
            property_names.extend(msg['properties'])
        
        logging.info('[%s] Discovering Clusters', self.hostname)
        
	try:
            result = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                                  obj_type=MORTypes.ClusterComputeResource)
	except Exception as e:
            logging.warning("Cannot discover Clusters: %s", e)
            return { "success": -1, "msg": "Cannot discover Clusters: %s" % e }

        data = [{p.Name:p.Val for p in item.PropSet} for item in result]

        return { "success": 0,
                 "msg": "Successfully discovered Clusters",
                 "result": data,
                 }
