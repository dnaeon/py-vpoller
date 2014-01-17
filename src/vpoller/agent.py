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
    def get_host_property(self, msg):
        """
        Get property of an object of type HostSystem and return it.

        Example client message to get a host property could be:

            {
                "method":     "host.poll",
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
        # Sanity check for required attributes in the message
        if not all(k in msg for k in ("name", "properties")):
            return { "success": -1, "msg": "Missing message properties (e.g. name/properties)" }

        # Check if we are connected first
        if not self.viserver.is_connected():
            self.reconnect()

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
                   "msg": "Successfully retrieved property",
                   "result": {p.Name:p.Val for p in ps},
                   }
        
        return result
            
    def get_datastore_property(self, msg):
        """
        Get property of an object of type Datastore and return it.

        Example client message to get a host property could be:

            {
                "method":     "datastore.poll",
                "hostname":   "vc01-test.example.org",
                "info.url":   "ds:///vmfs/volumes/5190e2a7-d2b7c58e-b1e2-90b11c29079d/",
                "properties": [
                    "summary.capacity",
                    "info.freeSpace",
                ]
            }
        
        Args:
            msg (dict): The client message to process
        
        """
        # Sanity check for required attributes in the message
        if not all(k in msg for k in ("info.url", "properties")):
            return { "success": -1, "msg": "Missing message properties (e.g. info.url/properties)" }

        # Check if we are connected first
        if not self.viserver.is_connected():
            self.reconnect()

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

        logging.info('[%s] Retrieving %s for datastore %s', self.hostname, msg['properties'], msg['info.url'])

        self.update_datastore_mors()
        mor = self.mors_cache['Datastore']['objects'].get(msg['info.url'])

        if not mor:
            return { "success": -1, "msg": "Unable to find datastore %s" % msg['info.url'] }

        try:
            result = self.viserver._get_object_properties(mor=mor, property_names=property_names)
        except Exception as e:
            logging.warning("Cannot get property for datastore %s: %s" % (msg['info.url'], e))
            return { "success": -1, "msg": "Cannot get property for datastore %s: %s" % (msg['info.url'], e) }

        ps = result.get_element_propSet()

        result = { "success": 0,
                   "msg": "Successfully retrieved property",
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
        # Check if we are connected first
        if not self.viserver.is_connected():
            self.reconnect()
        
        # Properties we want to retrieve are 'name' and 'runtime.powerState'
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['name', 'runtime.powerState']

        if msg['properties']:
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
        # Check if we are connected first
        if not self.viserver.is_connected():
            self.reconnect()
        
        # Properties we want to retrieve about the datastores plus any
        # other user-requested properties
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['info.name', 'info.url', 'summary.accessible']

        if msg['properties']:
            property_names.extend(msg['properties'])
        
        logging.info('[%s] Discovering datastores', self.hostname)
        
        # Retrieve the data
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
    
