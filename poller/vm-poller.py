#!/usr/bin/env python

"""
'vm-poller' is an application used for polling information from a VMware vCenter server.

It is intended to be integrated into a Zabbix template for polling ESX hosts and Datastores properties.

The current poller is based on the vm-poller.py used by the VMware Stats App.

Author: Marin Atanasov Nilolov <mnikolov@vmware.com>
"""

import os
import sys
import getopt
import syslog
import ConfigParser

import pysphere

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
        syslog.syslog('Getting property %s for %s from vCenter %s' % (prop, name, self._vcenter))

        property_names = ['name',
                          prop
                          ]

        try:
            results = self._viserver._retrieve_properties_traversal(property_names=property_names,
                                                                obj_type=pysphere.MORTypes.HostSystem)
        except pysphere.resources.vi_exception.VIApiException, e:
            syslog.syslog(syslog.LOG_ERR, 'Failed to get properties for %s' % name)
            raise VMPollerException, 'Cannot get properties: %s' % e

        # iterate over the results and find our host with 'name'
        for item in results:
            d = {}

            for p in item.PropSet:
                d[p.Name] = p.Val

            # return the property if found and break
            if d['name'] == name:
                return d[prop]

        return None
            
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
        syslog.syslog('Getting property %s for %s from vCenter %s' % (prop, name, self._vcenter))

        property_names = ['info.name',
                          'info.url',
                          prop
                          ]

        try:
            results = self._viserver._retrieve_properties_traversal(property_names=property_names,
                                                                obj_type=pysphere.MORTypes.Datastore)
        except pysphere.resources.vi_exception.VIApiException, e:
            syslog.syslog(syslog.LOG_ERR, 'Failed to get properties for %s' % name)
            raise VMPollerException, 'Cannot get properties: %s' % e

        # iterate over the results and find our datastore with 'name' and 'url'
        for item in results:
            d = {}

            for p in item.PropSet:
                d[p.Name] = p.Val

            if d['info.name'] == name and d['info.url'] == url:
                return d[prop]

        return None
                
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
        print poller.get_datastore_property(name, ds_url, myProperty)
    elif pollInfo == 'hosts':
        print poller.get_host_property(name, myProperty)
        
    poller.disconnect()
   
if __name__ == '__main__':
    main()

