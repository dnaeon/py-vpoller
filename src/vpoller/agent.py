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

import json
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
                "method":    "host.poll",
                "hostname":  "vc01-test.example.org",
                "name"     : "esxi01-test.example.org",
                "property" : "hardware.memorySize"
            }
        
        Args:
            msg (dict): The client message to process

        """
        # Sanity check for required attributes in the message
        if not all(k in msg for k in ("name", "property")):
            return "{ \"success\": -1, \"msg\": \"Missing message properties (e.g. name/property)\" }"

        # Check if we are connected first
        if not self.viserver.is_connected():
            self.reconnect()
        
        # Search is done by using the 'name' property of the ESXi Host as
        # this uniquely identifies the host
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['name', msg['property']]

        logging.info('[%s] Retrieving %s for host %s', self.hostname, msg['property'], msg['name'])

        # Get the properties for all registered hosts
        try:
            results = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                                   obj_type=MORTypes.HostSystem)
        except Exception as e:
	    logging.warning("Cannot get property for host %s: %s", msg["name"], e)
            return "{ \"success\": -1, \"msg\": \"Cannot get property for host %s: %s\" }" % (msg["name"], e)

        # Do we have something to return?
        if not results:
            return "{ \"success\": -1, \"msg\": \"Did not find property %s for host %s\" }" % (msg["property"], msg["name"])

        # Find the host we are looking for
        for item in results:
            props = [(p.Name, p.Val) for p in item.PropSet]
            d = dict(props)

            # Break if we have a match
            if d["name"] == msg["name"]:
                break
        else:
            return "{ \"success\": -1, \"msg\": \"Unable to find ESXi host %s\" }" % msg["name"]

        result = "{ \"status\": 0, \"msg\": \"Successfully retrieved property\", \"result\": \"%s\" }" % json.dumps(d)

        return result
            
    def get_datastore_property(self, msg):
        """
        Get property of an object of type Datastore and return it.

        Example client message to get a host property could be:

            {
                "method":   "datastore.poll",
                "hostname": "vc01-test.example.org",
                "info.url": "ds:///vmfs/volumes/5190e2a7-d2b7c58e-b1e2-90b11c29079d/",
                "property": "summary.capacity"
            }
        
        Args:
            msg (dict): The client message to process
        
        """
        # Sanity check for required attributes in the message
        if not all(k in msg for k in ("info.url", "property")):
            return "{ \"success\": -1, \"msg\": \"Missing message properties (e.g. info.url/property)\" }"

        # Check if we are connected first
        if not self.viserver.is_connected():
            self.reconnect()
        
        # Search is done by using the 'info.url' property as
        # this uniquely identifies the datastore
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        # 
        property_names = ['info.url', msg['property']]

        logging.info('[%s] Retrieving %s for datastore %s', self.hostname, msg['property'], msg['info.url'])

        try:
            results = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                                   obj_type=MORTypes.Datastore)
        except Exception as e:
            logging.warning("Cannot get property for datastore %s: %s" % (msg["info.url"], e))
            return "{ \"success\": -1, \"msg\": \"Cannot get property for datastore %s: %s\" }" % (msg["info.url"], e)

        if not results:
            return "{ \"success\": -1, \"msg\": \"Did not find property %s for datastore %s\" }" % (msg["property"], msg["info.url"])
        
        # Iterate over the results and find our datastore
        for item in results:
            props = [(p.Name, p.Val) for p in item.PropSet]
            d = dict(props)

            # break if we have a match
            if d['info.url'] == msg['info.url']:
                break
        else:
            return "{ \"success\": -1, \"msg\": \"Unable to find datastore %s\" }" % msg["info.url"]

        result = "{ \"status\": 0, \"msg\": \"Successfully retrieved property\", \"result\": \"%s\" }" % json.dumps(d)

        return result
        
    def discover_hosts(self, msg):
        """
        Discovers all ESXi hosts registered in the VMware vSphere server.

        Example client message to discover all ESXi hosts could be:

            {
                "method":   "host.discover",
                "hostname": "vc01-test.example.org",
                "zabbix"  : False,
            }

        If "zabbix" attribute is set to True then the result will be formatted
        in a way that the Zabbix Low-Level Discovery protocol can understand and use.

        For more information about Zabbix Low-Level Discovery, please check the link below:

          - https://www.zabbix.com/documentation/2.2/manual/discovery/low_level_discovery
              
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

        logging.info('[%s] Discovering ESXi hosts', self.hostname)

        # Retrieve the data
	try:
            results = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                                   obj_type=MORTypes.HostSystem)
	except Exception as e:
            logging.warning("Cannot discover hosts: %s", e)
            return "{ \"success\": -1, \"msg\": \"Cannot discover ESXi hosts: %s\" }" % e

        # Iterate over the results and prepare the JSON object
        data = []
        for item in results:
            # Do we want to return the data in Zabbix LLD format?
            # The names of the properties we return is in Zabbix Macro-like format, e.g.
            #
            #   {#vSphere.<property-name>}: <value>
            #
            # We also keep the vSphere host so we can use it later in Zabbix items
            if msg.get('zabbix'):
                props = [('{#vSphere.' + p.Name + '}', p.Val) for p in item.PropSet]
                props.append(('{#vSphere.Host}', self.hostname))
            else:
                props = [(p.Name, p.Val) for p in item.PropSet]

            d = dict(props)
            data.append(d)

        # Return result in Zabbix LLD format
        if msg.get('zabbix'):
            return "{ \"data\": %s }" % json.dumps(data)

        return "{ \"success\": 0, \"msg\": \"Successfully discovered ESXi hosts\", \"result\": %s }" % json.dumps(data)

    def discover_datastores(self, msg):
        """
        Discovers all datastores registered in a VMware vSphere server.

        Example client message to discover all datastores could be:
        
            {
                "method":   "datastore.discover",
        	"hostname": "vc01-test.example.org",
                "zabbix"  : False,
            }

        If "zabbix" attribute is set to True then the result will be formatted
        in a way that the Zabbix Low-Level Discovery protocol can understand and use.

        For more information about Zabbix Low-Level Discovery, please check the link below:

          - https://www.zabbix.com/documentation/2.2/manual/discovery/low_level_discovery
              
        Returns:
            The returned data is a JSON object, containing the discovered datastores.

        """
        # Check if we are connected first
        if not self.viserver.is_connected():
            self.reconnect()
        
        # Properties we want to retrieve about the datastores
        #
        # Check the vSphere Web Services SDK API for more information on the properties
        #
        #     https://www.vmware.com/support/developer/vc-sdk/
        #
        property_names = ['info.name', 'info.url', 'summary.accessible']
        
        logging.info('[%s] Discovering datastores', self.hostname)
        
        # Retrieve the data
	try:
            results = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                                   obj_type=MORTypes.Datastore)
	except Exception as e:
            logging.warning("Cannot discover datastores: %s", e)
            return "{ \"success\": -1, \"msg\": \"Cannot discover datastores: %s\" }" % e

        # Iterate over the results and prepare the JSON object
        data = []
        for item in results:
            # Do we want to return the data in Zabbix LLD format?
            # The names of the properties we return is in Zabbix Macro-like format, e.g.
            #
            #   {#vSphere.<property-name>}: <value>
            #
            # We also keep the vSphere host so we can use it later in Zabbix items
            if msg.get('zabbix'):
                props = [('{#vSphere.' + p.Name + '}', p.Val) for p in item.PropSet]
                props.append(('{#vSphere.Host}', self.hostname))
            else:
                props = [(p.Name, p.Val) for p in item.PropSet]

            d = dict(props)
            data.append(d)

        # Return result in Zabbix LLD format
        if msg.get('zabbix'):
            return "{ \"data\": %s }" % json.dumps(data)

        return "{ \"success\": 0, \"msg\": \"Successfully discovered datastores\", \"result\": %s }" % json.dumps(data)
