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
vSphere Agent Datacenter Tasks

"""

import pyVmomi

from vpoller.agent.core import task


@task(name='datacenter.discover', required=['hostname', 'name'])
def datacenter_discover(agent, msg):
    """
    Discover all vim.Datacenter managed objects
    
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
    # Property names to be collected
    properties = ['name']
    if 'properties' in msg and msg['properties']:
        properties.extend(msg['properties'])
        
    r = agent._discover_objects(
        properties=properties,
        obj_type=pyVmomi.vim.Datacenter
    )

    return r

@task(name='datacenter.get', required=['hostname', 'name'])
def datacenter_get(agent, msg):
    """
    Get properties of a single vim.Datacenter managed object
    
    Example client message would be:

    {
        "method":     "datacenter.get",
        "hostname":   "vc01.example.org",
        "name":       "MyDatacenter",
        "properties": [
            "name",
            "overallStatus"
        ]
    }
    
    Returns:
        The managed object properties in JSON format

    """
    # Property names to be collected
    properties = ['name']
    if 'properties' in msg and msg['properties']:
        properties.extend(msg['properties'])

    return agent._get_object_properties(
        properties=properties,
        obj_type=pyVmomi.vim.Datacenter,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

@task(name='datacenter.alarm.get', required=['hostname', 'name'])
def datacenter_alarm_get(agent, msg):
    """
    Get all alarms for a vim.Datacenter managed object
    
    Example client message would be:
    
    {
        "method":   "datacenter.alarm.get",
        "hostname": "vc01.example.org",
        "name":     "MyDatacenter"
    }
    
    Returns:
        The discovered alarms in JSON format
    
    """
    result = agent._object_alarm_get(
        obj_type=pyVmomi.vim.Datacenter,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

    return result
