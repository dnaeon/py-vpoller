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
vSphere Agent Network Tasks

"""

import logging

import pyVmomi

from vpoller.agent.core import task

@task(name='net.discover', required=['hostname'])
def net_discover(agent, msg):
    """
    Discover all pyVmomi.vim.Network managed objects

    Example client message would be:

    {
        "method":   "net.discover",
        "hostname": "vc01.example.org",
    }

    Example client message which also requests additional properties:

    {
        "method":     "net.discover",
        "hostname":   "vc01.example.org",
        "properties": [
            "name",
            "summary.accessible"
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
        obj_type=pyVmomi.vim.Network
    )

    return r

@task(name='net.get', required=['hostname', 'name'])
def net_get(agent, msg):
    """
    Get properties of a single pyVmomi.vim.Network managed object

    Example client message would be:

    {
        "method":     "net.get",
        "hostname":   "vc01.example.org",
        "name":       "VM Network",
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
        obj_type=pyVmomi.vim.Network,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

@task(name='net.host.get', required=['hostname', 'name'])
def net_host_get(agent, msg):
    """
    Get all Host Systems using this pyVmomi.vim.Network managed object

    Example client message would be:

    {
        "method":     "net.host.get",
        "hostname":   "vc01.example.org",
        "name":       "VM Network",
    }

    Returns:
        The managed object properties in JSON format

    """
    logging.debug(
        '[%s] Getting hosts using %s vim.Network managed object',
        agent.host,
        msg['name']
    )

    # Find the Network managed object and get the 'host' property
    data = agent._get_object_properties(
        properties=['name', 'host'],
        obj_type=pyVmomi.vim.Network,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

    if data['success'] != 0:
        return data

    props = data['result'][0]
    network_name, network_hosts = props['name'], props['host']

    # Create a list view for the HostSystem managed objects
    view_ref = agent.get_list_view(obj=network_hosts)
    result = {}
    result['name'] = network_name
    result['host'] = agent.collect_properties(
        view_ref=view_ref,
        obj_type=pyVmomi.vim.HostSystem,
        path_set=['name']
    )

    view_ref.DestroyView()

    r = {
        'success': 0,
        'msg': 'Successfully discovered objects',
        'result': result,
    }

    logging.debug('[%s] Returning result from operation: %s', agent.host, r)

    return r

@task(name='net.vm.get', required=['hostname', 'name'])
def net_vm_get(agent, msg):
    """
    Get all Virtual Machines using this pyVmomi.vim.Network managed object

    Example client message would be:

    {
        "method":     "net.vm.get",
        "hostname":   "vc01.example.org",
        "name":       "VM Network",
    }

    Returns:
        The managed object properties in JSON format

    """
    logging.debug(
        '[%s] Getting VMs using %s vim.Network managed object',
        agent.host,
        msg['name']
    )

    # Find the Network managed object and get the 'vm' property
    data = agent._get_object_properties(
        properties=['name', 'vm'],
        obj_type=pyVmomi.vim.Network,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

    if data['success'] != 0:
        return data

    props = data['result'][0]
    network_name, network_vms = props['name'], props['vm']

    # Create a list view for the VirtualMachine managed objects
    view_ref = agent.get_list_view(obj=network_vms)
    result = {}
    result['name'] = network_name
    result['vm'] = agent.collect_properties(
        view_ref=view_ref,
        obj_type=pyVmomi.vim.VirtualMachine,
        path_set=['name']
    )

    view_ref.DestroyView()

    r = {
        'success': 0,
        'msg': 'Successfully discovered objects',
        'result': result,
    }

    logging.debug('[%s] Returning result from operation: %s', agent.host, r)

    return r
