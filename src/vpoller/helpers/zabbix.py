# Copyright (c) 2013-2015 Marin Atanasov Nikolov <dnaeon@gmail.com>
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
vPoller Zabbix Helper module

The vPoller Zabbix Helper module provides routines for
translating a result vPoller message to a Zabbix-friendly format.

"""

import json
import logging


class HelperAgent(object):
    """
    HelperAgent class of the Zabbix vPoller Helper

    """
    def __init__(self, msg, data):
        """
        Initializes a new HelperAgent object

        Args:
            msg  (dict): The original request message
            data (dict): The data to be processed by the helper

        """
        self.msg = msg
        self.data = data

        # Methods that the Helper knows about and how to process
        self.methods = {
            'about': self.zabbix_item_value,
            'event.latest': self.zabbix_item_value,
            'session.get': self.zabbix_lld_data,
            'datacenter.discover': self.zabbix_lld_data,
            'datacenter.get': self.zabbix_item_value,
            'datacenter.alarm.get': self.zabbix_lld_data,
            'datacenter.perf.metric.get': self.zabbix_item_value,
            'datacenter.perf.metric.info': self.zabbix_lld_data,
            'cluster.alarm.get': self.zabbix_lld_data,
            'cluster.discover': self.zabbix_lld_data,
            'cluster.get': self.zabbix_item_value,
            'cluster.perf.metric.get': self.zabbix_item_value,
            'cluster.perf.metric.info': self.zabbix_lld_data,
            'host.alarm.get': self.zabbix_lld_data,
            'host.discover': self.zabbix_lld_data,
            'host.get': self.zabbix_item_value,
            'host.vm.get': self.zabbix_lld_data,
            'host.datastore.get': self.zabbix_lld_data,
            'host.cluster.get': self.zabbix_item_value,
            'host.perf.metric.get': self.zabbix_item_value,
            'host.perf.metric.info': self.zabbix_lld_data,
            'vm.alarm.get': self.zabbix_lld_data,
            'vm.discover': self.zabbix_lld_data,
            'vm.get': self.zabbix_item_value,
            'vm.datastore.get': self.zabbix_lld_data,
            'vm.disk.discover': self.zabbix_vm_disk_discover,
            'vm.disk.get': self.zabbix_vm_disk_get,
            'vm.host.get': self.zabbix_item_value,
            'vm.process.get': self.zabbix_vm_process_get,
            'vm.cpu.usage.percent': self.zabbix_item_value,
            'vm.perf.metric.get': self.zabbix_item_value,
            'vm.perf.metric.info': self.zabbix_lld_data,
            'vm.snapshot.get': self.zabbix_lld_data,
            'datastore.alarm.get': self.zabbix_lld_data,
            'datastore.discover': self.zabbix_lld_data,
            'datastore.get': self.zabbix_item_value,
            'datastore.host.get': self.zabbix_lld_data,
            'datastore.vm.get': self.zabbix_lld_data,
            'datastore.perf.metric.get': self.zabbix_item_value,
            'datastore.perf.metric.info': self.zabbix_lld_data,
            'vsan.health.get': self.zabbix_item_value,
        }

    def run(self):
        """
        Main Helper method

        Processes the data and does any translations if needed

        """
        logging.debug('[zbx-helper]: Initiating data processing')
        logging.debug(
            '[zbx-helper]: Original client task request: %s',
            self.msg
        )
        logging.debug(
            '[zbx-helper]: Received data for processing: %s',
            self.data
        )

        # Check whether the request was successful first
        if self.data['success'] != 0:
            logging.debug(
                '[zbx-helper]: Task request was not successful (exitcode: %d)',
                self.data['success']
            )
            logging.debug(
                '[zbx-helper]: No processing will be done by the helper'
            )
            return self.data['msg']

        # The original method requested by the client
        self.method = self.msg['method']

        if self.method not in self.methods:
            logging.warning(
                '[zbx-helper]: Do not know how to process %s method',
                self.method
            )
            return '[zbx-helper]: Do not know how to process %s method' % self.method

        logging.debug(
            '[zbx-helper]: Processing data using %s() method',
            self.methods[self.method].__name__
        )
        
        result = self.methods[self.method]()

        logging.debug(
            '[zbx-helper]: Returning result after data processing: %s',
            result
        )

        return json.dumps(result, ensure_ascii=False)

    def zabbix_item_value(self):
        """
        Processes a single property value

        The value we return is of the first property only,
        so that each item in Zabbix stores a single property value.

        Returns:
            The property value from the result message

        """
        property_name = self.msg['properties'][0]
        result = self.data['result'][-1]

        return result.get(property_name)

    def zabbix_vm_disk_get(self):
        """
        Processes a single property value for a VM guest disk

        The value we return is of the first property only,
        so that each item in Zabbix stores a single property value.

        Returns:
            The property value from the result message

        """
        property_name = self.msg['properties'][0]
        result = self.data['result'][0]['disk']

        return result.get(property_name)

    def zabbix_vm_disk_discover(self):
        """
        Translates a VM disk discovery request to Zabbix LLD format

        This method translates a discovery request to the
        Zabbix Low-Level Discovery format.

        For more information about Zabbix LLD,
        please refer to link below:

            - https://www.zabbix.com/documentation/2.2/manual/discovery/low_level_discovery

        The result attribute names are in Zabbix Macro-like format, e.g.

            {#VSPHERE.<TYPE>.<ATTRIBUTE>}: <value>

        """
        obj_t = self.method.split('.')[0].upper()
        result = self.data['result'][0]['disk']

        data = []

        for item in result:
            props = [('{#VSPHERE.' + obj_t + '.' + k.upper() + '}', v) for k, v in item.items()]
            data.append(dict(props))

        return {'data': data}

    def zabbix_vm_process_get(self):
        """
        Returns the number of processes in a Virtual Machine

        Matching for specific processes in the Virtual Machine is
        done by passing the 'key' attribute in the original client
        task request.

        """
        processes = self.data['result']

        if 'key' in self.msg and self.msg['key']:
            result = len([p for p in processes if self.msg['key'] in p['cmdLine']])
        else:
            result = len(processes)

        return result

    def zabbix_lld_data(self):
        """
        Translates a discovery request to Zabbix LLD format

        This method translates a discovery request to the
        Zabbix Low-Level Discovery format.

        For more information about Zabbix LLD,
        please refer to link below:

            - https://www.zabbix.com/documentation/2.2/manual/discovery/low_level_discovery

        The result attribute names are in Zabbix Macro-like format, e.g.

            {#VSPHERE.<TYPE>.<ATTRIBUTE>}: <value>

        """
        # Get the vPoller method name without the last part of it,
        # which is usually the operation performed like '.get' and
        # '.discover'. From that method name construct the macro
        # which will be used in Zabbix.
        m = self.method.split('.')[:-1]
        method_name = '.'.join(m).upper()
        result = self.data['result']

        data = []
        for item in result:
            props = [('{#VSPHERE.' + method_name + '.' + k.upper() + '}', v) for k, v in item.items()]
            data.append(dict(props))

        return {'data': data}
