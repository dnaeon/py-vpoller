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
vm-discoverer.py is an application used for auto-discovery of VMware vSphere objects.

It is intended to be integrated into a Zabbix template for auto-discovery of VMware vSphere objects,
which makes it suitable for auto-discovering VMware ESX hosts, VMs, Datastores, etc.

The data is returned in JSON format that is recognizable by Zabbix and ready for importing by the
auto-discovery protocol used by Zabbix.
"""

import os
import sys
import json
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
    """
    VMPoller class.

    The VMPoller class defines methods for auto-discovery of
    VMware vSphere objects.

    Uses the VMware vSphere Web SDK API.

    """
    def __init__(self, config):
        """
        Initializes a new VMPoller object.

        """
        self._vcenter  = config.get('Default', 'vcenter')
        self._username = config.get('Default', 'username')
        self._password = config.get('Default', 'password')
        self._viserver = pysphere.VIServer()

    def vcenter(self):
        """
        Returns the VMware vCenter server the poller is connected to.

        """
        return self._vcenter
    
    def connect(self):
        """
        Connect to a VMware vCenter server.

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
        Disconnect from a VMware vCenter server.

        """
        syslog.syslog('Disconnecting from vCenter %s' % self._vcenter)
        self._viserver.disconnect()

    def discover_hosts(self):
        """
        Discoveres all ESX hosts registered in the VMware vCenter server.

        Returns:
            The returned data is a JSON object, containing the discovered ESX hosts.

        """
        syslog.syslog('Discovering ESX hosts on vCenter %s' % self._vcenter)

        # Properties we will poll from the vCenter
        property_names = ['name',
                          'runtime.powerState',
                          ]

        # Property macros for Zabbix use
        property_macros = {'name': 		 '{#ESX_NAME}',
                           'runtime.powerState': '{#ESX_POWERSTATE}',
                           }

        # Retrieve the data
        results = self._viserver._retrieve_properties_traversal(property_names=property_names,
                                                                obj_type=pysphere.MORTypes.HostSystem)

        json_data = []
        for item in results:
            d = {}

            for p in item.PropSet:
                # convert bool objects to integers, so that Zabbix can recognize them
                if isinstance(p.Val, bool):
                    d[property_macros[p.Name]] = int(p.Val)
                else:
                    d[property_macros[p.Name]] = p.Val

            # remember on which vCenter this ESX host runs on
            d['{#VCENTER_SERVER}'] = self._vcenter
            json_data.append(d)

        # print what we've discovered
        print json.dumps({ 'data': json_data}, indent=4)

    def discover_datastores(self):
        """
        Discovers all datastores registered in a VMware vCenter server.

        Returns:
            The returned data is a JSON object, containing the discovered datastores.

        """
        syslog.syslog('Discovering datastores on vCenter %s' % self._vcenter)

        # Properties we will poll from the VMware vCenter server
        property_names = ['info.name',
                          'info.url',
                          'summary.accessible',
                          ]

        # Property <name>-<macro> mappings for use by Zabbix
        property_macros = {'info.name': 	 '{#DS_NAME}',
                           'info.url':		 '{#DS_URL}',
                           'summary.accessible': '{#DS_ACCESSIBLE}',
                           }

        # Retrieve the data
        results = self._viserver._retrieve_properties_traversal(property_names=property_names,
                                                                obj_type=pysphere.MORTypes.Datastore)

        json_data = []
        for item in results:
            d = {}

            for p in item.PropSet:
                # Convert bool objects to integers, so that Zabbix can recognize the data
                if isinstance(p.Val, bool):
                    d[property_macros[p.Name]] = int(p.Val)
                else:
                    d[property_macros[p.Name]] = p.Val

            # remember on which vCenter is this datastore
            d['{#VCENTER_SERVER}'] = self._vcenter
            json_data.append(d)

        # print what we've discovered
        print json.dumps({ 'data': json_data}, indent=4)

def parse_config(conf):
    """
    Parses a configuration file.

    Returns:
        ParserConfig object containing the configuration details for this poller connection.

    Raises:
        IOError

    """
    if not os.path.exists(conf):
        raise IOError, 'Config file %s does not exists' % conf

    config = ConfigParser.ConfigParser()
    config.read(conf)

    return config
                
def main():
    """
    Main

    """
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

