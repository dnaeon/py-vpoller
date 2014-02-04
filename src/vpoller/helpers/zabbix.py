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
vPoller Zabbix Helper module

The vPoller Zabbix Helper module provides routines for
translating a result vPoller message to a Zabbix-friendly format.

"""

import json

class HelperAgent(object):
    """
    HelperAgent class of the Zabbix vPoller Helper

    """
    def __init__(self, msg, data):
        """
        Initializes a new HelperAgent object

        Args:
            msg  (dict): The original request message
            data  (str): The result message data
            
        """
        self.msg = msg
        self.data = json.loads(data)

    def run(self):
        """
        Main Helper method

        Processes the data and does any translations if needed

        """
        # Check whether the request was successful first
        if self.data['success'] != 0:
            return json.dumps(self.data, indent=4)

        # The original method requested from the vPoller Workers
        method = self.msg['method']
        
        # Methods that the Helper knows about and how to process
        methods = {
            'host.get':           self.zabbix_item_value,
            'datastore.get':      self.zabbix_item_value,
            'host.discover':      self.zabbix_lld_data,
            'datastore.discover': self.zabbix_lld_data,
            }
        
        result = methods[method]() if methods.get(method) else '[zbx-helper]: Do not know how to process method %s' % method

        return result

    def zabbix_item_value(self):
        """
        Processes a single property value

        Returns:
            The property value from the result message

        """
        property_name = self.msg['property']
        
        return self.data['result'][property_name]

    def zabbix_lld_data(self):
        """
        Translates a discovery request to Zabbix LLD format

        This method translates a discovery request to the
        Zabbix Low-Level Discovery format.
        
        For more information about Zabbix LLD, please refer to link below:

            - https://www.zabbix.com/documentation/2.2/manual/discovery/low_level_discovery

        The result attribute names are in Zabbix Macro-like format, e.g.

            {#vSphere.<attribute>}: <value>
            
        """
        result = self.data['result']

        data = []
        
        for eachItem in result:
            props = [('{#vSphere.' + k + '}', v) for k, v in eachItem.items()]
            data.append(dict(props))

        return json.dumps({ 'data': data }, indent=4)
                
