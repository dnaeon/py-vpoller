#!/usr/bin/env python

"""
'vm-discoverer' is an application used for polling information from a VMware vCenter server.

It is intended to be integrated into a Zabbix template for auto discovery of ESX hosts and datastores.

The data is returned in JSON format that is recognizable by Zabbix and ready for importing by the
auto discovery protocol used by Zabbix.

The current poller is based on the vm-poller.py used by the VMware Stats App.

Author: mnikolov@vmware.com
"""

import os
import sys
import json
import getopt
import syslog
import ConfigParser

import pysphere

class VMPollerException(Exception):
    pass

class VMPoller(object):
    def __init__(self, config):
        self._vcenter  = config.get('Default', 'vcenter')
        self._username = config.get('Default', 'username')
        self._password = config.get('Default', 'password')
        self._viserver = pysphere.VIServer()

    def vcenter(self):
        return self._vcenter
    
    def connect(self):
        syslog.syslog('Connecting to vCenter %s' % self._vcenter)
        
        try:
            self._viserver.connect(host=self._vcenter, user=self._username, password=self._password)
        except:
            syslog.syslog(syslog.LOG_ERR, 'Failed to connect to vCenter %s' % self._vcenter)
            raise VMPollerException, 'Cannot connect to vCenter %s' % self._vcenter

    def disconnect(self):
        syslog.syslog('Disconnecting from vCenter %s' % self._vcenter)
        self._viserver.disconnect()

    def discover_hosts(self):
        syslog.syslog('Discovering ESX hosts on vCenter %s' % self._vcenter)

        property_names = ['name',
                          'runtime.powerState',
                          ]

        property_macros = {'name': 		 '{#ESX_NAME}',
                           'runtime.powerState': '{#ESX_POWERSTATE}',
                           }

        results = self._viserver._retrieve_properties_traversal(property_names=property_names,
                                                                obj_type=pysphere.MORTypes.HostSystem)

        json_data = []
        
        for item in results:
            d = {}

            for p in item.PropSet:
                if isinstance(p.Val, bool):
                    d[property_macros[p.Name]] = int(p.Val)
                else:
                    d[property_macros[p.Name]] = p.Val

            # remember on which vCenter this ESX host runs on
            d['{#VCENTER_SERVER}'] = self._vcenter
                
            json_data.append(d)
        
        print json.dumps({ 'data': json_data}, indent=4)

    def discover_datastores(self):
        syslog.syslog('Discovering datastores on vCenter %s' % self._vcenter)

        property_names = ['info.name',
                          'info.url',
                          'summary.accessible',
                          ]

        property_macros = {'info.name': 	 '{#DS_NAME}',
                           'info.url':		 '{#DS_URL}',
                           'summary.accessible': '{#DS_ACCESSIBLE}',
                           }
        
        results = self._viserver._retrieve_properties_traversal(property_names=property_names,
                                                                obj_type=pysphere.MORTypes.Datastore)

        json_data = []
        
        for item in results:
            d = {}

            for p in item.PropSet:
                if isinstance(p.Val, bool):
                    d[property_macros[p.Name]] = int(p.Val)
                else:
                    d[property_macros[p.Name]] = p.Val

            # remember on which vCenter is this datastore
            d['{#VCENTER_SERVER}'] = self._vcenter

            json_data.append(d)

        print json.dumps({ 'data': json_data}, indent=4)

def parse_config(conf):
    if not os.path.exists(conf):
        raise IOError, 'Config file %s does not exists' % conf

    config = ConfigParser.ConfigParser()
    config.read(conf)

    return config
                
def main():

    if len(sys.argv) != 4:
        print 'usage: %s [-D|-H] -f config' % sys.argv[0]
        raise SystemExit
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "DHf:")
    except getopt.GetoptError, e:
        print 'usage: %s [-D|-H] -f <config>' % sys.argv[0]
        raise SystemExit

    for opt, arg in opts:
        if opt == '-f':
            myConfig = arg
        elif opt == '-D':
            pollInfo = 'datastores'
        elif opt == '-H':
            pollInfo = 'hosts'

    config = parse_config(myConfig)
    poller = VMPoller(config)

    # Let's dance ...
    poller.connect()

    if pollInfo == 'datastores':
        poller.discover_datastores()
    elif pollInfo == 'hosts':
        poller.discover_hosts()
        
    poller.disconnect()
   
if __name__ == '__main__':
    main()

