#!/usr/bin/env python

"""
'vm-poller' is an application used for polling information from a VMware vCenter server.

It is intended to be integrated into a Zabbix template for polling ESX hosts and Datastores properties.

The current poller is based on the vm-poller.py used by the VMware Stats App.

Author: Marin Atanasov Nilolov <mnikolov@vmware.com>
"""

import os
import sys
import time
import getopt
import syslog
import ConfigParser

import pysphere

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

class VMPollerException(Exception):
    """
    Generic VMPoller exception.

    """
    pass

class VMPoller(object):
    def __init__(self, config):
        """
        Initialize the VMPoller object.

        """
        self._vcenter  = config.get('Default', 'vcenter')
        self._username = config.get('Default', 'username')
        self._password = config.get('Default', 'password')
        self._viserver = pysphere.VIServer()

    def vcenter(self):
        """
        Return the vCenter name we are running the poller against.

        """
        return self._vcenter
    
    def connect(self):
        """
        Connect to the vCenter we run the poller against.

        Raises:
            VMPollerException

        """
        syslog.syslog('Connecting to vCenter %s' % self._vcenter)
        
        try:
            self._viserver.connect(host=self._vcenter, user=self._username, password=self._password)
        except:
            syslog.syslog(syslog.LOG_ERR, 'Failed to connect to vCenter %s' % self._vcenter)
            raise VMPollerException, 'Cannot connect to vCenter %s' % self._vcenter

    def disconnect(self):
        """
        Disconnect the poller from the vCenter.

        """
        syslog.syslog('Disconnecting from vCenter %s' % self._vcenter)
        self._viserver.disconnect()

    def get_host_property(self, name, prop):
        """
        Get property of an object of type HostSystem and return it.

        Args:
            name    (str): Name of the host object
            prop    (str): Name of the property as defined by the vSphere SDK API

        Returns:
            The requested property value

        """

        # dictionary mapping for properties and helper functions used for
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
            'summary.rebootRequired':				return_as_int,
            'summary.quickStats.distributedCpuFairness':	return_as_is,
            'summary.quickStats.uptime':			return_as_is,
            'summary.quickStats.overallCpuUsage':		return_as_hz,
            'summary.quickStats.overallMemoryUsage':		return_as_bytes,
            'summary.quickStats.distributedMemoryFairness':	return_as_bytes,
            'runtime.inMaintenanceMode':			return_as_int,
            'summary.config.vmotionEnabled':			return_as_int,
            'runtime.bootTime':					return_as_time,
        }

        # Custom properties, which are not available in the vSphere Web SDK
        # Keys are the property names and values are a list of the properties required to
        # calculate the custom properties
        custom_zabbix_host_properties = {}

        # Basic set of required properties, which are needed to find the host in question
        property_names = ['name']

        # Flag to indicate whether a custom property has been requested or a standard one
        custom_property_requested = False
        
        if prop in zabbix_host_properties:
            property_names.append(prop)
        elif prop in custom_zabbix_host_properties:
            property_names = property_names + custom_zabbix_host_properties[prop]['properties']
            custom_property_requested = True
        else:
            syslog.syslog('Invalid property name passed: %s' % prop)
            return None

        syslog.syslog('Getting property %s for %s from vCenter %s' % (prop, name, self._vcenter))

        try:
            results = self._viserver._retrieve_properties_traversal(property_names=property_names,
                                                                obj_type=pysphere.MORTypes.HostSystem)
        except pysphere.resources.vi_exception.VIApiException, e:
            syslog.syslog(syslog.LOG_ERR, 'Failed to get properties for %s' % name)
            raise VMPollerException, 'Cannot get properties: %s' % e

        # iterate over the results and find our host with 'name'
        for item in results:
            d = {}

            # fill up the properties in the dictionary
            for p in item.PropSet:
                d[p.Name] = p.Val

            # return the property if found and break
            if d['name'] == name:
                if prop not in d:
                    return 0 # Return zero here and not None, so that Zabbix can understand the value

                if custom_property_requested:
                    return custom_zabbix_host_properties[prop]['function'](d)
                else:
                    return zabbix_host_properties[prop](d[prop])

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
            syslog.syslog('Invalid property name passed: %s' % prop)
            return None
        
        syslog.syslog('Getting property %s for %s from vCenter %s' % (prop, name, self._vcenter))

        try:
            results = self._viserver._retrieve_properties_traversal(property_names=property_names,
                                                                obj_type=pysphere.MORTypes.Datastore)
        except pysphere.resources.vi_exception.VIApiException, e:
            syslog.syslog(syslog.LOG_ERR, 'Failed to get properties for %s' % name)
            raise VMPollerException, 'Cannot get properties: %s' % e

        # iterate over the results and find our datastore with 'name' and 'url'
        for item in results:
            d = {}

            # fill up all properties in the dictionary
            for p in item.PropSet:
                d[p.Name] = p.Val

            # return the result back to Zabbix if we have a match
            if d['info.name'] == name and d['info.url'] == url:
                if prop not in d:
                    return 0 # Return zero here and not None so that Zabbix understands the value

                if custom_property_requested:
                    return custom_zabbix_datastore_properties[prop]['function'](d)
                else:
                    return zabbix_datastore_properties[prop](d[prop])

        return 0
                
def parse_config(conf):
    if not os.path.exists(conf):
        raise IOError, 'Config file %s does not exists' % conf

    config = ConfigParser.ConfigParser()
    config.read(conf)

    return config
                
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

    config = parse_config(myConfig)
    poller = VMPoller(config)

    # Let's dance ...
    poller.connect()

    if pollInfo == 'datastores':
        result = poller.get_datastore_property(name, ds_url, myProperty)
    elif pollInfo == 'hosts':
        result = poller.get_host_property(name, myProperty)

    poller.disconnect()

    print result
    
if __name__ == '__main__':
    main()

