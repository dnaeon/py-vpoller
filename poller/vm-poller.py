#!/usr/bin/env python
#
# Copyright (c) 2013 Marin Atanasov Nikolov <dnaeon@gmail.com>
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
vm-poller.py is an application used for polling objects' information from a VMware vCenter server.

It is intended to be integrated into a Zabbix template for polling of ESX hosts and Datastores properties.
"""

import os
import sys
import time
import getopt
import syslog
import vmconnector
from pysphere import MORTypes

class VMPollerException(Exception):
    """
    Generic VMPoller exception.

    """
    pass

class VMPoller(vmconnector.VMConnector):
    """
    VMPoller class.

    Defines methods for retrieving vSphere objects' properties.

    Extends:
        VMConnector

    """
    def get_host_property(self, name, prop):
        """
        Get property of an object of type HostSystem and return it.

        Args:
            name    (str): Name of the host
            prop    (str): Name of the property as defined by the vSphere SDK API

        Returns:
            The requested property value

        """
        # dictionary mapping of properties and helper functions used for
        # converting property values to proper types before passing the values to Zabbix
        zabbix_host_properties = {
            'name':						return_as_is,
            'hardware.memorySize':				return_as_is,
            'hardware.cpuInfo.hz':				return_as_is,
            'hardware.cpuInfo.numCpuCores':			return_as_is,
            'hardware.cpuInfo.numCpuPackages':			return_as_is,
            'runtime.connectionState':				return_as_is,
            'runtime.powerState':				return_as_is,
            'summary.managementServerIp':			return_as_is,
            'summary.overallStatus':				return_as_is,
            'summary.quickStats.distributedCpuFairness':	return_as_is,
            'summary.quickStats.uptime':			return_as_is,
            'summary.quickStats.overallCpuUsage':		return_as_hz,
            'summary.quickStats.overallMemoryUsage':		return_as_bytes,
            'summary.quickStats.distributedMemoryFairness':	return_as_bytes,
            'runtime.inMaintenanceMode':			return_as_int,
            'summary.config.vmotionEnabled':			return_as_int,
            'summary.rebootRequired':				return_as_int,
            'runtime.bootTime':					return_as_time,
        }

        # Custom properties, which are not available in the vSphere Web SDK
        # Keys are the property names and the value is a dict defining the basic
        # set of properties required and a handler which returns the result
        custom_zabbix_host_properties = {}

        # Basic set of required properties, which are needed to find the host in question
        property_names = ['name']

        # Flag to indicate whether a custom property has been requested or a standard one
        custom_property_requested = False

        # Sanity check of the provided property name
        if prop in zabbix_host_properties:
            property_names.append(prop)
        elif prop in custom_zabbix_host_properties:
            property_names = property_names + custom_zabbix_host_properties[prop]['properties']
            custom_property_requested = True
        else:
            syslog.syslog('[%s] Invalid property name passed: %s' % (self.vcenter, prop))
            return None

        syslog.syslog('[%s] Retrieving %s for host %s' % (self.vcenter, prop, name))

        # retrieve the properties
        results = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                               obj_type=MORTypes.HostSystem)

        # iterate over the results and find our host with 'name'
        for item in results:
            d = {}

            # fill up the properties in the dictionary
            for p in item.PropSet:
                d[p.Name] = p.Val

            # return the property if found and break
            if d['name'] == name:
                if custom_property_requested:
                    return custom_zabbix_host_properties[prop]['function'](d)
                elif prop in d and not custom_property_requested:
                    return zabbix_host_properties[prop](d[prop])
                else:
                    return 0 # Return zero here and not None, so that Zabbix can understand the value

        return 0
            
    def get_datastore_property(self, name, url, prop):
        """
        Get property of an object of type Datastore and return it.

        Args:
            name    (str): Name of the datatstore object
            url     (str): Datastore URL
            prop    (str): Name of the property as defined by the vSphere SDK API

        Returns:
            The requested property value

        """

        # dictionary mapping for properties and helper functions used for
        # converting property values to proper types before passing the values to Zabbix
        zabbix_datastore_properties = {
            'info.name':					return_as_is,
            'info.maxFileSize':					return_as_is,
            'info.url':						return_as_is,
            'summary.capacity':					return_as_is,
            'summary.freeSpace':				return_as_is,
            'summary.maintenanceMode':				return_as_is,
            'summary.type':					return_as_is,
            'summary.uncommitted':				return_as_is,
            'summary.accessible':				return_as_int,
            'info.timestamp':					return_as_time,
        }

        # Custom properties, which are not available in the vSphere Web SDK
        # Keys are the property names and values are a list of the properties required to
        # calculate the custom properties
        custom_zabbix_datastore_properties = {
            'datastore_used_space_percentage': {
                'properties': ['summary.freeSpace', 'summary.capacity'],
                'function'  : datastore_used_space_percentage,
             }
        }

        # Basic set of required properties, which are needed to find the datastore in question
        property_names = ['info.name', 'info.url']

        # Flag to indicate whether a custom property has been requested or a standard one
        custom_property_requested = False
        
        if prop in zabbix_datastore_properties:
            property_names.append(prop)
        elif prop in custom_zabbix_datastore_properties:
            property_names = property_names + custom_zabbix_datastore_properties[prop]['properties']
            custom_property_requested = True
        else:
            syslog.syslog('[%s] Invalid property name passed: %s' % (self.vcenter, prop))
            return None
        
        syslog.syslog('[%s] Retrieving %s for datastore %s' % (self.vcenter, prop, name))

        results = self.viserver._retrieve_properties_traversal(property_names=property_names,
                                                               obj_type=MORTypes.Datastore)
        
        # iterate over the results and find our datastore with 'name' and 'url'
        for item in results:
            d = {}

            # fill up all properties in the dictionary
            for p in item.PropSet:
                d[p.Name] = p.Val

            # return the result back to Zabbix if we have a match
            if d['info.name'] == name and d['info.url'] == url:

                if custom_property_requested:
                    return custom_zabbix_datastore_properties[prop]['function'](d)
                elif prop in d and not custom_property_requested:
                    return zabbix_datastore_properties[prop](d[prop])
                else:
                    return 0

        return 0

def return_as_is(val):
    """
    Helper function, which returns property value as-is

    """
    return val

def return_as_time(val):
    """
    Helper function, which returns property value as time

    """
    return time.strftime('%Y-%m-%d %H:%M:%S', val)

def return_as_int(val):
    """
    Helper function, which returns property value as integer

    """
    return int(val)

def return_as_bytes(val):
    """
    Helper function, which returns property value as bytes

    """
    return val * 1048576

def return_as_hz(val):
    """
    Helper function, which returns property value as hz

    """
    return val * 1048576

def datastore_used_space_percentage(d):
    """
    Calculate the used datastore space in percentage

    """
    return round(100 - (float(d['summary.freeSpace']) / float(d['summary.capacity']) * 100), 2)
    
def main():

    if len(sys.argv) != 10:
        print 'usage: %s [-D|-H] -n <name> -p <property> [-u <datastore-url> -f <config>' % sys.argv[0]
        raise SystemExit
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "DHn:p:u:f:")
    except getopt.GetoptError, e:
        print 'usage: %s [-D|-H] -n <name> -p <property> [-u <datastore-url>] -f <config>' % sys.argv[0]
        raise SystemExit

    for opt, arg in opts:
        if opt == '-f':
            myConfig = arg
        elif opt == '-p':
            myProperty = arg
        elif opt == '-n':
            name = arg
        elif opt == '-u':
            ds_url = arg
        elif opt == '-D':
            pollInfo = 'datastores'
        elif opt == '-H':
            pollInfo = 'hosts'

    config = vmconnector.load_config(myConfig)
    poller = VMPoller(config)

    # Let's dance ...
    poller.connect(ignore_locks=True)

    if pollInfo == 'datastores':
        result = poller.get_datastore_property(name, ds_url, myProperty)
    elif pollInfo == 'hosts':
        result = poller.get_host_property(name, myProperty)

    poller.disconnect()

    print result
    
if __name__ == '__main__':
    main()

