#!/usr/bin/env python

"""
'vm-poller' is an application used for polling information from a VMware vCenter server.

It is intended to be integrated into a Zabbix template for auto discovery of ESX hosts and VMs.

The data is returned in JSON format that is recognizable by Zabbix and ready for importing by the
auto discovery protocol used by Zabbix.

The current poller is based on the vm-poller.py used by the VMware Stats App.

Author: mnikolov@vmware.com
"""

import os
import sys
import json
import time
import getopt
import syslog
import ConfigParser

import pysphere

LOCK_DIR = '/var/run/vm-poller'

class VMPollerException(Exception):
    pass

class VMPoller(object):
    def __init__(self, config):
        self._vcenter  = config.get('Default', 'vcenter')
        self._username = config.get('Default', 'username')
        self._password = config.get('Default', 'password')

        self._lockfile = '%s/%s.lock' % (LOCK_DIR, self._vcenter)
        
        self._viserver = pysphere.VIServer()

        if not os.path.exists(LOCK_DIR):
            os.mkdir(LOCK_DIR)
        
    def vcenter(self):
        return self._vcenter
    
    def connect(self):
        if os.path.exists(self._lockfile):
            syslog.syslog('Lock file exists for vCenter %s, aborting ...' % self._vcenter)
            raise SystemExit

        syslog.syslog('Connecting to vCenter %s' % self._vcenter)
        
        # create a lock file
        with open(self._lockfile, 'w') as lockfile:
            lockfile.write(str(os.getpid()))
        
        try:
            self._viserver.connect(host=self._vcenter, user=self._username, password=self._password)
        except:
            syslog.syslog(syslog.LOG_ERR, 'Failed to connect to vCenter %s' % self._vcenter)
            raise VMPollerException, 'Cannot connect to vCenter %s' % self._vcenter

    def disconnect(self):
        syslog.syslog('Disconnecting from vCenter %s' % self._vcenter)

        # remove the lock file
        os.unlink(self._lockfile)

        self._viserver.disconnect()

    def poll_hosts(self):
        syslog.syslog('Polling hosts information from vCenter %s' % self._vcenter)

        property_names = ['name',
                          'hardware.memorySize',
                          'hardware.cpuInfo.hz',
                          'hardware.cpuInfo.numCpuCores',
                          'hardware.cpuInfo.numCpuPackages',
                          'runtime.bootTime',
                          'runtime.connectionState',
                          'runtime.inMaintenanceMode',
                          'runtime.powerState',
                          'summary.config.vmotionEnabled',
                          'summary.managementServerIp',
                          'summary.overallStatus',
                          'summary.rebootRequired',
                          'summary.quickStats.distributedCpuFairness',
                          'summary.quickStats.distributedMemoryFairness',
                          'summary.quickStats.overallCpuUsage',
                          'summary.quickStats.overallMemoryUsage',
                          'summary.quickStats.uptime',
                          ]

        property_macros = {'name': 						'{#ESX_NAME}',
                           'hardware.memorySize':				'{#ESX_MEMORY_SIZE}',
                           'hardware.cpuInfo.hz':				'{#ESX_CPU_INFO_HZ}',
                           'hardware.cpuInfo.numCpuCores':			'{#ESX_CPU_NUM_CORES}',
                           'hardware.cpuInfo.numCpuPackages':			'{#ESX_CPU_NUM_PKGS}',
                           'runtime.bootTime':					'{#ESX_BOOT_TIME}',
                           'runtime.connectionState':				'{#ESX_CONNECTION_STATE}',
                           'runtime.inMaintenanceMode':				'{#ESX_IN_MAINTENANCE_MODE}',
                           'runtime.powerState':				'{#ESX_POWERSTATE}',
                           'summary.config.vmotionEnabled':			'{#ESX_VMOTION_ENABLED}',
                           'summary.managementServerIp':			'{#ESX_MGMT_IP}',
                           'summary.overallStatus':				'{#ESX_OVERALL_STATUS}',
                           'summary.rebootRequired':				'{#ESX_REBOOT_REQUIRED}',
                           'summary.quickStats.distributedCpuFairness':		'{#ESX_DISTRIBUTED_CPU_FAIRNESS}',
                           'summary.quickStats.distributedMemoryFairness':	'{#ESX_DISTRIBUTED_MEM_FAIRNESS}',
                           'summary.quickStats.overallCpuUsage':		'{#ESX_OVERALL_CPU_USAGE}',
                           'summary.quickStats.overallMemoryUsage':		'{#ESX_OVERALL_MEM_USAGE}',
                           'summary.quickStats.uptime':				'{#ESX_UPTIME}',
                          }

        results = self._viserver._retrieve_properties_traversal(property_names=property_names,
                                                                obj_type=pysphere.MORTypes.HostSystem)

        json_data = []
        
        for item in results:
            d = {}

            for p in item.PropSet:
                if p.Name == 'runtime.bootTime':
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', p.Val)
                    d[property_macros[p.Name]] = timestamp
                else:
                    d[property_macros[p.Name]] = p.Val

            json_data.append(d)
        
        print json.dumps({ 'data': json_data}, indent=4)

    def poll_datastores(self):
        syslog.syslog('Polling datastores information from vCenter %s' % self._vcenter)

        property_names = ['info.name',
                          'info.maxFileSize',
                          'info.timestamp',
                          'info.url',
                          'summary.accessible',
                          'summary.capacity',
                          'summary.freeSpace',
                          'summary.maintenanceMode',
                          'summary.type',
                          'summary.uncommitted'
                          ]

        property_macros = {'info.name':			'{#DS_NAME}',
                           'info.maxFileSize':		'{#DS_MAXFILE_SIZE}',
                           'info.timestamp':		'{#DS_TIMESTAMP}',
                           'info.url':			'{#DS_URL}',
                           'summary.accessible':	'{#DS_ACCESSIBLE}',
                           'summary.capacity':		'{#DS_CAPACITY}',
                           'summary.freeSpace':		'{#DS_FREESPACE}',
                           'summary.maintenanceMode':	'{#DS_MAINTENANCE_MODE}',
                           'summary.type':		'{#DS_TYPE}',
                           'summary.uncommitted':	'{#DS_UNCOMMITTED}',
                           }
        
        results = self._viserver._retrieve_properties_traversal(property_names=property_names,
                                                                obj_type=pysphere.MORTypes.Datastore)

        json_data = []
        
        for item in results:
            d = {}

            for p in item.PropSet:
                if p.Name == 'info.timestamp':
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', p.Val)
                    d[property_macros[p.Name]] = timestamp
                else:
                    d[property_macros[p.Name]] = p.Val
                
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
        print 'usage: %s -f config' % sys.argv[0]
        raise SystemExit
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f:DH")
    except getopt.GetoptError, e:
        print 'usage: %s -f config' % sys.argv[0]
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
        poller.poll_datastores()
    elif pollInfo == 'hosts':
        poller.poll_hosts()
        
    poller.disconnect()
   
if __name__ == '__main__':
    main()

