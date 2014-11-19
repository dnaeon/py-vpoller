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
vSphere Agent Resource Pool Tasks

"""

import pyVmomi

from vpoller.agent.core import task

@task(name='resource.pool.discover', required=['hostname'])
def resource_pool_discover(self, msg):
    """
    Discover all vim.ResourcePool managed objects

    Example client message would be:

    {
        "method":   "resource.pool.discover",
        "hostname": "vc01.example.org",
    }

    Example client message which also requests additional properties:

    {
        "method":     "resource.pool.discover",
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
        obj_type=pyVmomi.vim.ResourcePool
    )

    return r

@task(name='resource.pool.get', required=['hostname', 'name'])
def resource_pool_get(agent, msg):
    """
    Get properties of a single vim.ResourcePool managed object

    Example client message would be:

    {
        "method":     "resource.pool.get",
        "hostname":   "vc01.example.org",
        "name":       "MyResourcePool",
        "properties": [
            "name",
            "runtime.cpu",
            "runtime.memory",
            "runtime.overallStatus"
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
        obj_type=pyVmomi.vim.ResourcePool,
        obj_property_name='name',
        obj_property_value=msg['name']
    )
