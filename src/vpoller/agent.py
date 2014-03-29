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

Check the vSphere Web Services SDK API for more information on the properties
you can request for any specific vSphere managed object

    - https://www.vmware.com/support/developer/vc-sdk/

"""

import logging

import zmq
import pyVmomi
from vpoller.core import VPollerException
from vpoller.connector import VConnector

class VSphereAgent(VConnector):
    """
    VSphereAgent class

    Defines methods for retrieving vSphere object properties

    These are the worker agents that do the actual polling from the vSphere host

    Extends:
        VConnector

    """
    def datacenter_discover(self, msg):
        """
        Discover all pyVmomi.vim.Datacenter managed objects

        Example client message would be:
        
            {
                "method":   "datacenter.discover",
        	"hostname": "vc01.example.org",
            }

        Example client message which also requests additional properties:

            {
                "method":     "datacenter.discover",
                "hostname":   "vc01.example.org",
                "properties": [
                    "name",
                    "overallStatus"
                ]
            }
              
        Returns:
            The discovered objects in JSON format

        """
        logging.info('[%s] Discovering pyVmomi.vim.Datacenter managed objects', self.host)

        # Property names to be collected
        properties = ['name']
        if msg.has_key('properties') and msg['properties']:
            properties.extend(msg['properties'])

        view_ref = self.get_datacenter_view()
        try: 
            data = self.collect_properties(
                view_ref=view_ref,
                obj_type=pyVmomi.vim.Datacenter,
                path_set=properties
            )
        except Exception as e:
            return { 'success': -1, 'msg': 'Cannot discover objects: %s' % e}

        result = {
            'success': 0,
            'msg': 'Successfully discovered objects',
            'result': data,
        }

        logging.debug('Returning result to client: %s', result)

        return result
    
    def host_discover(self, msg):
        """
        Discover all pyVmomi.vim.HostSystem managed objects

        Example client message would be:
        
            {
                "method":   "host.discover",
        	"hostname": "vc01.example.org",
            }

        Example client message which also requests additional properties:

            {
                "method":     "host.discover",
                "hostname":   "vc01.example.org",
                "properties": [
                    "name",
                    "runtime.powerState"
                ]
            }
              
        Returns:
            The discovered objects in JSON format

        """
        logging.info('[%s] Discovering pyVmomi.vim.HostSystem managed objects', self.host)

        # Property names to be collected
        properties = ['name']
        if msg.has_key('properties') and msg['properties']:
            properties.extend(msg['properties'])

        view_ref = self.get_host_view()
        try: 
            data = self.collect_properties(
                view_ref=view_ref,
                obj_type=pyVmomi.vim.HostSystem,
                path_set=properties
            )
        except Exception as e:
            return { 'success': -1, 'msg': 'Cannot discover objects: %s' % e}

        result = {
            'success': 0,
            'msg': 'Successfully discovered objects',
            'result': data,
        }

        logging.debug('Returning result to client: %s', result)

        return result
