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
VMware vSphere tasks module for vPoller

For more information about the VMware vSphere SDK,
which this module is using please check the link below:

    - https://www.vmware.com/support/developer/vc-sdk/

"""


import pyVmomi

from vpoller.log import logger
from vpoller.task.decorators import task


def _discover_objects(agent, properties, obj_type):
    """
    Helper method to simplify discovery of vSphere managed objects

    This method is used by the '*.discover' vPoller Worker methods and is
    meant for collecting properties for multiple objects at once, e.g.
    during object discovery operation.

    Args:
        agent         (VConnector): Instance of VConnector
        properties          (list): Properties to be collected
        obj_type   (pyVmomi.vim.*): Type of vSphere managed object

    Returns:
        The discovered objects in JSON format

    """
    logger.info(
        '[%s] Discovering %s managed objects',
        agent.host,
        obj_type.__name__
    )

    view_ref = agent.get_container_view(obj_type=[obj_type])
    try:
        data = agent.collect_properties(
            view_ref=view_ref,
            obj_type=obj_type,
            path_set=properties
        )
    except Exception as e:
        return {'success': 1, 'msg': 'Cannot collect properties: {}'.format(e.message)}

    view_ref.DestroyView()

    result = {
        'success': 0,
        'msg': 'Successfully discovered objects',
        'result': data,
    }

    return result

def _get_object_properties(agent,
                           properties,
                           obj_type,
                           obj_property_name,
                           obj_property_value,
                           include_mors=False):
    """
    Helper method to simplify retrieving of properties

    This method is used by the '*.get' vPoller Worker methods and is
    meant for collecting properties for a single managed object.

    We first search for the object with property name and value,
    then create a list view for this object and
    finally collect it's properties.

    Args:
        agent            (VConnector): A VConnector instance
        properties             (list): List of properties to be collected
        obj_type       pyVmomi.vim.*): Type of vSphere managed object
        obj_property_name       (str): Property name used for searching for the object
        obj_property_value      (str): Property value identifying the object in question

    Returns:
        The collected properties for this managed object in JSON format

    """
    logger.info(
        '[%s] Retrieving properties for %s managed object of type %s',
        agent.host,
        obj_property_value,
        obj_type.__name__
    )

    # Find the Managed Object reference for the requested object
    try:
        obj = agent.get_object_by_property(
            property_name=obj_property_name,
            property_value=obj_property_value,
            obj_type=obj_type
        )
    except Exception as e:
        return {'success': 1, 'msg': 'Cannot collect properties: {}'.format(e.message)}

    if not obj:
        return {
            'success': 1,
            'msg': 'Cannot find object {}'.format(obj_property_value)
        }

    # Create a list view for this object and collect properties
    view_ref = agent.get_list_view(obj=[obj])

    try:
        data = agent.collect_properties(
            view_ref=view_ref,
            obj_type=obj_type,
            path_set=properties,
            include_mors=include_mors
        )
    except Exception as e:
        return {'success': 1, 'msg': 'Cannot collect properties: {}'.format(e.message)}

    view_ref.DestroyView()

    result = {
        'success': 0,
        'msg': 'Successfully retrieved object properties',
        'result': data,
    }

    return result

def _object_datastore_get(agent, obj_type, name):
    """
    Helper method used for getting the datastores available to an object

    This method searches for the managed object with 'name' and retrieves
    the 'datastore' property which contains all datastores available/used
    by the managed object, e.g. VirtualMachine, HostSystem.

    Args:
        agent       (VConnector): A VConnector instance
        obj_type (pyVmomi.vim.*): Managed object type
        name               (str): Name of the managed object, e.g. host, vm

    Returns:
        The discovered objects in JSON format

    """
    logger.debug(
        '[%s] Getting datastores for %s managed object of type %s',
        agent.host,
        name,
        obj_type.__name__
    )

    # Find the object by it's 'name' property
    # and get the datastores available/used by it
    data = _get_object_properties(
        agent=agent,
        properties=['datastore'],
        obj_type=obj_type,
        obj_property_name='name',
        obj_property_value=name
    )

    if data['success'] != 0:
        return data

    # Get the name and datastore properties from the result
    props = data['result'][0]
    obj_datastores = props['datastore']

    # Get a list view of the datastores available/used by
    # this object and collect properties
    view_ref = agent.get_list_view(obj=obj_datastores)
    result = agent.collect_properties(
        view_ref=view_ref,
        obj_type=pyVmomi.vim.Datastore,
        path_set=['name', 'info.url']
    )

    view_ref.DestroyView()

    r = {
        'success': 0,
        'msg': 'Successfully discovered objects',
        'result': result,
    }

    return r

def _object_alarm_get(agent,
                      obj_type,
                      obj_property_name,
                      obj_property_value):
    """
    Helper method for retrieving alarms for a single Managed Object

    Args:
        agent            (VConnector): A VConnector instance
        obj_type      (pyVmomi.vim.*): Type of the Managed Object
        obj_property_name       (str): Property name used for searching for the object
        obj_property_value      (str): Property value identifying the object in question

    Returns:
        The triggered alarms for the Managed Object

    """
    logger.debug(
        '[%s] Retrieving alarms for %s managed object of type %s',
        agent.host,
        obj_property_value,
        obj_type.__name__
    )

    # Get the 'triggeredAlarmState' property for the managed object
    data = _get_object_properties(
        agent=agent,
        properties=['triggeredAlarmState'],
        obj_type=obj_type,
        obj_property_name=obj_property_name,
        obj_property_value=obj_property_value
    )

    if data['success'] != 0:
        return data

    result = []
    props = data['result'][0]
    alarms = props['triggeredAlarmState']
    for alarm in alarms:
        a = {
            'key': str(alarm.key),
            'info': alarm.alarm.info.name,
            'time': str(alarm.time),
            'entity': alarm.entity.name,
            'acknowledged': alarm.acknowledged,
            'overallStatus': alarm.overallStatus,
            'acknowledgedByUser': alarm.acknowledgedByUser,
        }
        result.append(a)

    r = {
        'success': 0,
        'msg': 'Successfully retrieved alarms',
        'result': result,
    }

    return r

def _get_counter_by_id(agent, counter_id):
    """
    Get a counter by its id

    Args:
        agent      (VConnector): A VConnector instance
        counter_id        (int): A counter ID

    Returns:
        A vim.PerformanceManager.CounterInfo instance

    """
    for c in agent.perf_counter:
        if c.key == counter_id:
            return c

    return None

def _get_counter_by_name(agent, name):
    """
    Get a counter by its name

    A counter name is expected to be in the following form:

        - <group>.<name>.<unit>.<rollup>

    Args:
        agent (VConnector): A VConnector instance
        name         (str): A counter name

    Returns:
        A vim.PerformanceManager.CounterInfo instance

    """
    for c in agent.perf_counter:
        c_name = '{}.{}.{}.{}'.format(c.groupInfo.key, c.nameInfo.key, c.unitInfo.key, c.rollupType)
        if name == c_name:
            return c

    return None

def _entity_perf_metric_info(agent, entity, counter_name=''):
    """
    Get info about supported performance metrics for a managed entity

    If the managed entity supports real-time statistics then
    return the real-time performance counters available for it,
    otherwise fall back to historical statistics only.

    Args:
        agent           (VConnector): A VConnector instance
        entity       (pyVmomi.vim.*): A managed entity to lookup
        counter_name           (str): Performance counter name

    Returns:
        Information about supported performance metrics for the entity

    """
    if not isinstance(entity, pyVmomi.vim.ManagedEntity):
        return {'success': 0, 'msg': '{} is not a managed entity'.format(entity)}

    if counter_name:
        counter_info = _get_counter_by_name(
            agent=agent,
            name=counter_name
        )
        if not counter_info:
            return {
                'success': 1,
                'msg': 'Unknown performance counter requested'
            }

    provider_summary = agent.si.content.perfManager.QueryPerfProviderSummary(
        entity=entity
    )

    logger.debug(
        '[%s] Entity %s supports real-time statistics: %s',
        agent.host,
        entity.name,
        provider_summary.currentSupported
    )
    logger.debug(
        '[%s] Entity %s supports historical statistics: %s',
        agent.host,
        entity.name,
        provider_summary.summarySupported
    )

    interval_id = provider_summary.refreshRate if provider_summary.currentSupported else None
    try:
        metric_id = agent.si.content.perfManager.QueryAvailablePerfMetric(
            entity=entity,
            intervalId=interval_id
        )
    except pyVmomi.vim.InvalidArgument as e:
        return {
            'success': 1,
            'msg': 'Cannot retrieve performance metrics for {1}: {2}'.format(entity.name, e)
        }

    if counter_name:
        data = [{k: getattr(m, k) for k in ('counterId', 'instance')} for m in metric_id if m.counterId == counter_info.key]
    else:
        data = [{k: getattr(m, k) for k in ('counterId', 'instance')} for m in metric_id]

    # Convert counter ids to human-friendly names
    for e in data:
        c_id = e['counterId']
        c_info = _get_counter_by_id(agent=agent, counter_id=c_id)
        e['counterId'] = '{}.{}.{}.{}'.format(c_info.groupInfo.key, c_info.nameInfo.key, c_info.unitInfo.key, c_info.rollupType)

    result = {
        'msg': 'Successfully retrieved performance metrics',
        'success': 0,
        'result': data
    }

    return result

def _entity_perf_metric_get(agent, entity, counter_name, max_sample=1, instance='', interval_name=None):
    """
    Retrieve performance metrics from a managed object

    Args:
        agent         (VConnector): A VConnector instance
        entity     (pyVmomi.vim.*): A managed entity (performance provider)
        counter_name         (str): A performance counter name
        max_sample           (int): Max samples to be retrieved
        instance             (str): Instance name, e.g. 'vmnic0'
        perf_interval_name   (str): Historical performance interval name

    Returns:
        The collected performance metrics from the managed object

    """
    logger.info(
        '[%s] Retrieving performance metric %s for %s',
        agent.host,
        counter_name,
        entity.name,
    )

    provider_summary = agent.si.content.perfManager.QueryPerfProviderSummary(
        entity=entity
    )

    logger.debug(
        '[%s] Entity %s supports real-time statistics: %s',
        agent.host,
        entity.name,
        provider_summary.currentSupported
    )
    logger.debug(
        '[%s] Entity %s supports historical statistics: %s',
        agent.host,
        entity.name,
        provider_summary.summarySupported
    )

    if not provider_summary.currentSupported and not interval_name:
        logger.warning(
            '[%s] No historical performance interval provided for entity %s',
            agent.host,
            entity.name
        )
        return {'success': 1, 'msg': 'No historical performance interval provided for entity {}'.format(entity.name)}

    # For real-time statistics use the refresh rate of the provider.
    # For historical statistics use one of the existing historical
    # intervals on the system.
    # For managed entities that support both real-time and historical
    # statistics in order to retrieve historical stats a valid
    # interval name should be provided.
    # By default we expect that the requested performance counters
    # are real-time only, so if you need historical statistics
    # make sure to pass a valid historical interval name.
    if interval_name:
        if interval_name not in [i.name for i in agent.perf_interval]:
            logger.warning(
                '[%s] Historical interval %s does not exists',
                agent.host,
                interval_name
            )
            return {'success': 1, 'msg': 'Historical interval {} does not exists'.format(interval_name)}
        else:
            interval_id = [i for i in agent.perf_interval if i.name == interval_name].pop().samplingPeriod
    else:
        interval_id = provider_summary.refreshRate

    counter_info = _get_counter_by_name(
        agent=agent,
        name=counter_name
    )

    if not counter_info:
        return {
            'success': 1,
            'msg': 'Unknown performance counter requested'
        }

    metric_id = pyVmomi.vim.PerformanceManager.MetricId(
        counterId=counter_info.key,
        instance=instance
    )

    # TODO: Be able to specify interval with startTime and endTime as well
    # TODO: Might want to be able to retrieve multiple metrics as well
    query_spec = pyVmomi.vim.PerformanceManager.QuerySpec(
        maxSample=max_sample,
        entity=entity,
        metricId=[metric_id],
        intervalId=interval_id
    )

    data = agent.si.content.perfManager.QueryPerf(
        querySpec=[query_spec]
    )

    result = []
    for sample in data:
        sample_info, sample_value = sample.sampleInfo, sample.value
        for value in sample_value:
            for s, v in zip(sample_info, value.value):
                d = {
                    'interval': s.interval,
                    'timestamp': str(s.timestamp),
                    'counterId': counter_name,
                    'instance': value.id.instance,
                    'value': v
                }
                result.append(d)

    r = {
        'msg': 'Successfully retrieved performance metrics',
        'success': 0,
        'result': result,
    }

    return r

@task(name='about')
def about(agent, msg):
    """
    Get the 'about' information for the vSphere host

    Example client message would be:

    {
        "method":   "about",
        "hostname": "vc01.example.org"
    }

    Example client message requesting additional properties:

    {
        "method":   "about",
        "hostname": "vc01.example.org"
        "properties": [
            "apiType",
            "apiVersion",
            "version"
        ]
    }

    Returns:
        The discovered objects in JSON format

    """
    logger.info("[%s] Retrieving vSphere About information", agent.host)

    # If no properties are specified just return the 'fullName' property
    if 'properties' not in msg or not msg['properties']:
        properties = ['fullName']
    else:
        properties = msg['properties']

    data = {prop: getattr(agent.si.content.about, prop, '(null)') for prop in properties}
    result = {
        'msg': 'Successfully retrieved properties',
        'success': 0,
        'result': [data],
    }

    return result

@task(name='event.latest')
def event_latest(agent, msg):
    """
    Get the latest event registered

    Example client message would be:

    {
        "method":   "event.latest",
        "hostname": "vc01.example.org",
    }

    Returns:
        The discovered objects in JSON format

    """
    logger.info('[%s] Retrieving latest registered event', agent.host)

    e = agent.si.content.eventManager.latestEvent.fullFormattedMessage

    result = {
        'msg': 'Successfully retrieved event',
        'success': 0,
        'result': [{'event': e}],
    }

    return result

@task(name='session.get')
def session_get(agent, msg):
    """
    Get the established vSphere sessions

    Example client message would be:

    {
        "method":   "session.get",
        "hostname": "vc01.example.org",
    }

    Returns:
        The established vSphere sessions in JSON format

    """
    logger.info('[%s] Retrieving established sessions', agent.host)

    try:
        sm = agent.si.content.sessionManager
        session_list = sm.sessionList
    except pyVmomi.vim.NoPermission:
        return {
            'msg': 'No permissions to view established sessions',
            'success': 1
        }

    # Session properties to be collected
    props = [
        'key',
        'userName',
        'fullName',
        'loginTime',
        'lastActiveTime',
        'ipAddress',
        'userAgent',
        'callCount'
    ]

    sessions = []
    for session in session_list:
        s = {k: str(getattr(session, k)) for k in props}
        sessions.append(s)

    result = {
        'msg': 'Successfully retrieved sessions',
        'success': 0,
        'result': sessions,
    }

    return result

@task(name='perf.metric.info')
def perf_metric_info(agent, msg):
    """
    Get all performance counters supported by the vSphere host

    Example client message would be:

    {
        "method":   "perf.metric.info",
        "hostname": "vc01.example.org",
    }

    Returns:
        The list of supported performance counters by the vSphere host

    """
    logger.info(
        '[%s] Retrieving supported performance counters',
        agent.host
    )

    data = []
    for c in agent.perf_counter:
        d = {
            'key': c.key,
            'nameInfo': {k: getattr(c.nameInfo, k) for k in ('label', 'summary', 'key')},
            'groupInfo': {k: getattr(c.groupInfo, k) for k in ('label', 'summary', 'key')},
            'unitInfo': {k: getattr(c.unitInfo, k) for k in ('label', 'summary', 'key')},
            'rollupType': c.rollupType,
            'statsType': c.statsType,
            'level': c.level,
            'perDeviceLevel': c.perDeviceLevel,
        }
        data.append(d)

    result = {
        'success': 0,
        'msg': 'Successfully retrieved performance metrics info',
        'result': data
    }

    return result

@task(name='perf.interval.info')
def perf_interval_info(agent, msg):
    """
    Get information about existing performance historical intervals

    Example client message would be:

    {
        "method":   "perf.interval.info",
        "hostname": "vc01.example.org",
    }

    Returns:
        The existing performance historical interval on the system

    """
    logger.info(
        '[%s] Retrieving existing performance historical intervals',
        agent.host
    )

    historical_interval = agent.si.content.perfManager.historicalInterval

    data = [{k: getattr(interval, k) for k in ('enabled', 'key', 'length', 'level', 'name', 'samplingPeriod')} for interval in historical_interval]

    result = {
        'msg': 'Successfully retrieved performance historical intervals',
        'success': 0,
        'result': data
    }

    return result

@task(name='net.discover')
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

    r = _discover_objects(
        agent=agent,
        properties=properties,
        obj_type=pyVmomi.vim.Network
    )

    return r

@task(name='net.get', required=['name'])
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

    return _get_object_properties(
        agent=agent,
        properties=properties,
        obj_type=pyVmomi.vim.Network,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

@task(name='net.host.get', required=['name'])
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
    logger.debug(
        '[%s] Getting hosts using %s vim.Network managed object',
        agent.host,
        msg['name']
    )

    # Find the Network managed object and get the 'host' property
    data = _get_object_properties(
        agent=agent,
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

    return r

@task(name='net.vm.get', required=['name'])
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
    logger.debug(
        '[%s] Getting VMs using %s vim.Network managed object',
        agent.host,
        msg['name']
    )

    # Find the Network managed object and get the 'vm' property
    data = _get_object_properties(
        agent=agent,
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

    return r

@task(name='datacenter.discover')
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

    r = _discover_objects(
        agent=agent,
        properties=properties,
        obj_type=pyVmomi.vim.Datacenter
    )

    return r

@task(name='datacenter.perf.metric.get', required=['name', 'counter-name', 'perf-interval'])
def datacenter_perf_metric_get(agent, msg):
    """
    Get performance metrics for a vim.Datacenter managed object

    A vim.Datacenter managed entity supports historical performance
    metrics only, so a valid historical performance interval
    should be provided as part of the client message.

    Example client message would be:

    {
        "method":   "datacenter.perf.metric.get",
        "hostname": "vc01.example.org",
        "name":     "MyDatacenter",
        "counter-name": vmop.numPoweron.number  # VM power on count
        "perf-interval": "Past day"  # Historical performance interval
    }

    Returns:
        The retrieved performance metrics

    """
    obj = agent.get_object_by_property(
        property_name='name',
        property_value=msg['name'],
        obj_type=pyVmomi.vim.Datacenter
    )

    if not obj:
        return {'success': 1, 'msg': 'Cannot find object: {}'.format(msg['name'])}

    counter_name = msg.get('counter-name')
    interval_name = msg.get('perf-interval')

    return _entity_perf_metric_get(
        agent=agent,
        entity=obj,
        counter_name=counter_name,
        interval_name = interval_name
    )

@task(name='datacenter.perf.metric.info')
def datacenter_perf_metric_info(agent, msg):
    """
    Get performance counters available for a vim.Datacenter object

    Example client message would be:

    {
        "method":      "datacenter.perf.metric.info",
        "hostname":    "vc01.example.org",
        "name":        "MyDatacenter",
        "counter-name": <counter-id>
    }

    Returns:
        Information about the supported performance counters for the object

    """
    obj = agent.get_object_by_property(
        property_name='name',
        property_value=msg['name'],
        obj_type=pyVmomi.vim.Datacenter
    )

    if not obj:
        return {'success': 1, 'msg': 'Cannot find object {}'.format(msg['name'])}

    counter_name = msg.get('counter-name')

    return _entity_perf_metric_info(
        agent=agent,
        entity=obj,
        counter_name=counter_name
    )

@task(name='datacenter.get', required=['name', 'properties'])
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

    return _get_object_properties(
        agent=agent,
        properties=properties,
        obj_type=pyVmomi.vim.Datacenter,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

@task(name='datacenter.alarm.get', required=['name'])
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
    result = _object_alarm_get(
        agent=agent,
        obj_type=pyVmomi.vim.Datacenter,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

    return result

@task(name='cluster.discover')
def cluster_discover(agent, msg):
    """
    Discover all vim.ClusterComputeResource managed objects

    Example client message would be:

    {
        "method":   "cluster.discover",
        "hostname": "vc01.example.org",
    }

    Example client message which also requests additional properties:

    {
        "method":     "cluster.discover",
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

    r = _discover_objects(
        agent=agent,
        properties=properties,
        obj_type=pyVmomi.vim.ClusterComputeResource
    )

    return r

@task(name='cluster.perf.metric.get', required=['name', 'counter-name', 'perf-interval'])
def cluster_perf_metric_get(agent, msg):
    """
    Get performance metrics for a vim.ClusterComputeResource managed object

    A vim.ClusterComputeResource managed entity supports historical
    statistics only, so make sure to provide a valid historical
    performance interval as part of the client message.

    Example client message would be:

    {
        "method":   "cluster.perf.metric.get",
        "hostname": "vc01.example.org",
        "name":     "MyCluster",
        "counter-name": clusterServices.effectivemem.megaBytes  # Effective memory resources
        "perf-interval": "Past day"  # Historical performance interval
    }

    Returns:
        The retrieved performance metrics

    """
    obj = agent.get_object_by_property(
        property_name='name',
        property_value=msg['name'],
        obj_type=pyVmomi.vim.ClusterComputeResource
    )

    if not obj:
        return {'success': 1, 'msg': 'Cannot find object: {}'.format(msg['name'])}

    counter_name = msg.get('counter-name')
    interval_name = msg.get('perf-interval')

    return _entity_perf_metric_get(
        agent=agent,
        entity=obj,
        counter_name=counter_name,
        interval_name=interval_name
    )

@task(name='cluster.perf.metric.info')
def cluster_perf_metric_info(agent, msg):
    """
    Get performance counters available for a vim.ClusterComputeResource object

    Example client message would be:

    {
        "method":      "cluster.perf.metric.info",
        "hostname":    "vc01.example.org",
        "name":        "MyCluster",
        "counter-name": <counter-name>
    }

    Returns:
        Information about the supported performance counters for the object

    """
    obj = agent.get_object_by_property(
        property_name='name',
        property_value=msg['name'],
        obj_type=pyVmomi.vim.ClusterComputeResource
    )

    if not obj:
        return {'success': 1, 'msg': 'Cannot find object {}'.format(msg['name'])}

    counter_name = msg.get('counter-name')

    return _entity_perf_metric_info(
        agent=agent,
        entity=obj,
        counter_name=counter_name
    )

@task(name='cluster.get', required=['name', 'properties'])
def cluster_get(agent, msg):
    """
    Get properties of a vim.ClusterComputeResource managed object

    Example client message would be:

    {
        "method":     "cluster.get",
        "hostname":   "vc01.example.org",
            "name":       "MyCluster",
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

    return _get_object_properties(
        agent=agent,
        properties=properties,
        obj_type=pyVmomi.vim.ClusterComputeResource,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

@task(name='cluster.alarm.get', required=['name'])
def cluster_alarm_get(agent, msg):
    """
    Get all alarms for a vim.ClusterComputeResource managed object

    Example client message would be:

    {
        "method":   "cluster.alarm.get",
        "hostname": "vc01.example.org",
        "name":     "MyCluster"
    }

    Returns:
        The discovered alarms in JSON format

    """
    result = _object_alarm_get(
        agent=agent,
        obj_type=pyVmomi.vim.ClusterComputeResource,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

    return result

@task(name='resource.pool.discover')
def resource_pool_discover(agent, msg):
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

    r = _discover_objects(
        agent=agent,
        properties=properties,
        obj_type=pyVmomi.vim.ResourcePool
    )

    return r

@task(name='resource.pool.get', required=['name', 'properties'])
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

    return _get_object_properties(
        agent=agent,
        properties=properties,
        obj_type=pyVmomi.vim.ResourcePool,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

@task(name='host.discover')
def host_discover(agent, msg):
    """
    Discover all vim.HostSystem managed objects

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
    # Property names to be collected
    properties = ['name']
    if 'properties' in msg and msg['properties']:
        properties.extend(msg['properties'])

    r = _discover_objects(
        agent=agent,
        properties=properties,
        obj_type=pyVmomi.vim.HostSystem
    )

    return r

@task(name='host.get', required=['name', 'properties'])
def host_get(agent, msg):
    """
    Get properties of a single vim.HostSystem managed object

    Example client message would be:

    {
        "method":     "host.get",
        "hostname":   "vc01.example.org",
        "name":       "esxi01.example.org",
        "properties": [
            "name",
            "runtime.powerState"
        ]
    }

    Returns:
        The managed object properties in JSON format

    """
    # Property names to be collected
    properties = ['name']
    if 'properties' in msg and msg['properties']:
        properties.extend(msg['properties'])

    return _get_object_properties(
        agent=agent,
        properties=properties,
        obj_type=pyVmomi.vim.HostSystem,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

@task(name='host.alarm.get', required=['name'])
def host_alarm_get(agent, msg):
    """
    Get all alarms for a vim.HostSystem managed object

    Example client message would be:

    {
        "method":   "host.alarm.get",
        "hostname": "vc01.example.org",
        "name":     "esxi01.example.org"
    }

    Returns:
        The discovered alarms in JSON format

    """
    result = _object_alarm_get(
        agent=agent,
        obj_type=pyVmomi.vim.HostSystem,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

    return result

@task(name='host.perf.metric.get', required=['name', 'counter-name'])
def host_perf_metric_get(agent, msg):
    """
    Get performance metrics for a vim.HostSystem managed object

    Example client message would be:

    {
        "method":       "host.perf.metric.get",
        "hostname":     "vc01.example.org",
        "name":         "esxi01.example.org",
        "counter-name": "net.usage.kiloBytesPerSecond",
        "instance":     "vmnic0",
        "max_sample": 1
    }

    Returns:
        The retrieved performance metrics

    """
    obj = agent.get_object_by_property(
        property_name='name',
        property_value=msg['name'],
        obj_type=pyVmomi.vim.HostSystem
    )

    if not obj:
        return {'success': 1, 'msg': 'Cannot find object: {}'.format(msg['name'])}

    if obj.runtime.powerState != pyVmomi.vim.HostSystemPowerState.poweredOn:
        return {'success': 1, 'msg': 'Host is not powered on, cannot get performance metrics'}

    if obj.runtime.connectionState != pyVmomi.vim.HostSystemConnectionState.connected:
        return {'success': 1, 'msg': 'Host is not connected, cannot get performance metrics'}

    try:
        counter_name = msg.get('counter-name')
        max_sample = int(msg.get('max-sample')) if msg.get('max-sample') else 1
        interval_name = msg.get('perf-interval')
        instance = msg.get('instance') if msg.get('instance') else ''
    except (TypeError, ValueError):
        logger.warning('Invalid message, cannot retrieve performance metrics')
        return {
            'success': 1,
            'msg': 'Invalid message, cannot retrieve performance metrics'
        }

    return _entity_perf_metric_get(
        agent=agent,
        entity=obj,
        counter_name=counter_name,
        max_sample=max_sample,
        instance=instance,
        interval_name=interval_name
    )

@task(name='host.perf.metric.info', required=['name'])
def host_perf_metric_info(agent, msg):
    """
    Get performance counters available for a vim.HostSystem object

    Example client message would be:

    {
        "method":       "host.perf.metric.info",
        "hostname":     "vc01.example.org",
        "name":         "esxi01.example.org",
        "counter-name": <counter-name>
    }

    Returns:
        Information about the supported performance counters for the object

    """
    obj = agent.get_object_by_property(
        property_name='name',
        property_value=msg['name'],
        obj_type=pyVmomi.vim.HostSystem
    )

    if not obj:
        return {'success': 1, 'msg': 'Cannot find object {}'.format(msg['name'])}

    counter_name = msg.get('counter-name')

    return _entity_perf_metric_info(
        agent=agent,
        entity=obj,
        counter_name=counter_name
    )

@task(name='host.cluster.get', required=['name'])
def host_cluster_get(agent, msg):
    """
    Get the cluster name for a HostSystem

    Example client message would be:

    {
        "method":     "host.cluster.get",
        "hostname":   "vc01.example.org",
        "name":       "esxi01.example.org",
    }

    Returns:
        The managed object properties in JSON format

    """
    logger.debug(
        '[%s] Getting cluster name for %s host',
        agent.host,
        msg['name']
    )

    # Find the HostSystem managed object and get the 'parent' property
    data = _get_object_properties(
        agent=agent,
        properties=['name', 'parent'],
        obj_type=pyVmomi.vim.HostSystem,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

    if data['success'] != 0:
        return data

    props = data['result'][0]
    host_name, host_cluster = props['name'], props['parent']

    result = {}
    result['name'] = host_name
    result['cluster'] = host_cluster.name

    r = {
        'success': 0,
        'msg': 'Successfully retrieved properties',
        'result': [result],
    }

    return r

@task(name='host.vm.get', required=['name'])
def host_vm_get(agent, msg):
    """
    Get all vim.VirtualMachine objects of a HostSystem

    Example client message would be:

        {
            "method":     "host.vm.get",
            "hostname":   "vc01.example.org",
            "name":       "esxi01.example.org",
        }

    Returns:
        The managed object properties in JSON format

    """
    logger.debug(
        '[%s] Getting VirtualMachine list running on %s host',
        agent.host,
        msg['name']
    )

    # Find the HostSystem managed object and get the 'vm' property
    data = _get_object_properties(
        agent=agent,
        properties=['vm'],
        obj_type=pyVmomi.vim.HostSystem,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

    if data['success'] != 0:
        return data

    props = data['result'][0]
    host_vms = props['vm']

    # Create a list view for the VirtualMachine managed objects
    view_ref = agent.get_list_view(obj=host_vms)
    result = agent.collect_properties(
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

    return r

@task(name='host.net.get', required=['name'])
def host_net_get(agent, msg):
    """
    Get all Networks used by a vim.HostSystem managed object

    Example client message would be:

        {
            "method":     "host.net.get",
            "hostname":   "vc01.example.org",
            "name":       "esxi01.example.org",
        }

    Returns:
        The managed object properties in JSON format

    """
    logger.debug(
        '[%s] Getting Network list available for %s host',
        agent.host,
        msg['name']
    )

    # Find the HostSystem managed object
    # and get the 'network' property
    data = _get_object_properties(
        agent=agent,
        properties=['name', 'network'],
        obj_type=pyVmomi.vim.HostSystem,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

    if data['success'] != 0:
        return data

    props = data['result'][0]
    host_name, host_networks = props['name'], props['network']

    # Create a list view for the Network managed objects
    view_ref = agent.get_list_view(obj=host_networks)
    result = {}
    result['name'] = host_name
    result['network'] = agent.collect_properties(
        view_ref=view_ref,
        obj_type=pyVmomi.vim.Network,
        path_set=['name']
    )

    view_ref.DestroyView()

    r = {
        'success': 0,
        'msg': 'Successfully discovered objects',
        'result': result,
    }

    return r

@task(name='host.datastore.get', required=['name'])
def host_datastore_get(agent, msg):
    """
    Get all Datastores used by a vim.HostSystem managed object

    Example client message would be:

        {
            "method":   "host.datastore.get",
            "hostname": "vc01.example.org",
            "name":     "esxi01.example.org",
        }

    Returns:
        The discovered objects in JSON format

    """
    return _object_datastore_get(
        agent=agent,
        obj_type=pyVmomi.vim.HostSystem,
        name=msg['name']
    )

@task(name='vm.alarm.get', required=['name'])
def vm_alarm_get(agent, msg):
    """
    Get all alarms for a vim.VirtualMachine managed object

    Example client message would be:

        {
            "method":   "vm.alarm.get",
            "hostname": "vc01.example.org",
            "name":     "vm01.example.org"
        }

    Returns:
        The discovered alarms in JSON format

    """
    result = _object_alarm_get(
        agent=agent,
        obj_type=pyVmomi.vim.VirtualMachine,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

    return result

@task(name='vm.perf.metric.get', required=['name', 'counter-name'])
def vm_perf_metric_get(agent, msg):
    """
    Get performance metrics for a vim.VirtualMachine managed object

    Example client message would be:

        {
            "method":       "vm.perf.metric.get",
            "hostname":     "vc01.example.org",
            "name":         "vm01.example.org",
            "counter-name": "cpu.usagemhz.megaHertz"
        }

    For historical performance statistics make sure to pass the
    performance interval as part of the message, e.g.:

        {
            "method":       "vm.perf.metric.get",
            "hostname":     "vc01.example.org",
            "name":         "vm01.example.org",
            "counter-name": "cpu.usage.megaHertz",
            "perf-interval": "Past day"
        }

    Returns:
        The retrieved performance metrics

    """
    obj = agent.get_object_by_property(
        property_name='name',
        property_value=msg['name'],
        obj_type=pyVmomi.vim.VirtualMachine
    )

    if not obj:
        return {'success': 1, 'msg': 'Cannot find object: {}'.format(msg['name'])}

    if obj.runtime.powerState != pyVmomi.vim.VirtualMachinePowerState.poweredOn:
        return {'success': 1, 'msg': 'VM is not powered on, cannot get performance metrics'}

    if obj.runtime.connectionState != pyVmomi.vim.VirtualMachineConnectionState.connected:
        return {'success': 1, 'msg': 'VM is not connected, cannot get performance metrics'}

    try:
        counter_name = msg.get('counter-name')
        max_sample = int(msg.get('max-sample')) if msg.get('max-sample') else 1
        interval_name = msg.get('perf-interval')
        instance = msg.get('instance') if msg.get('instance') else ''
    except (TypeError, ValueError):
        logger.warning('Invalid message, cannot retrieve performance metrics')
        return {
            'success': 1,
            'msg': 'Invalid message, cannot retrieve performance metrics'
        }

    return _entity_perf_metric_get(
        agent=agent,
        entity=obj,
        counter_name=counter_name,
        max_sample=max_sample,
        instance=instance,
        interval_name=interval_name
    )

@task(name='vm.perf.metric.info')
def vm_perf_metric_info(agent, msg):
    """
    Get performance counters available for a vim.VirtualMachine object

    Example client message would be:

        {
            "method":       "vm.perf.metric.info",
            "hostname":     "vc01.example.org",
            "name":         "vm01.example.org",
            "counter-name": "<counter-id>"
        }

    Returns:
        Information about the supported performance counters for the object

    """
    obj = agent.get_object_by_property(
        property_name='name',
        property_value=msg['name'],
        obj_type=pyVmomi.vim.VirtualMachine
    )

    if not obj:
        return {'success': 1, 'msg': 'Cannot find object {}'.format(msg['name'])}

    counter_name = msg.get('counter-name')

    return _entity_perf_metric_info(
        agent=agent,
        entity=obj,
        counter_name=counter_name
    )

@task(name='vm.discover')
def vm_discover(agent, msg):
    """
    Discover all pyVmomi.vim.VirtualMachine managed objects

    Example client message would be:

        {
            "method":   "vm.discover",
            "hostname": "vc01.example.org",
        }

    Example client message which also
    requests additional properties:

        {
            "method":     "vm.discover",
            "hostname":   "vc01.example.org",
            "properties": [
                "name",
                "runtime.powerState"
            ]
        }

    Returns:
        The discovered objects in JSON format

    """
    # Property names to be collected
    properties = ['name']
    if 'properties' in msg and msg['properties']:
        properties.extend(msg['properties'])

    r = _discover_objects(
        agent=agent,
        properties=properties,
        obj_type=pyVmomi.vim.VirtualMachine
    )

    return r

@task(name='vm.disk.discover', required=['name'])
def vm_disk_discover(agent, msg):
    """
    Discover all disks used by a vim.VirtualMachine managed object

    Note, that this request requires you to have
    VMware Tools installed in order get information about the
    guest disks.

    Example client message would be:

        {
            "method":   "vm.disk.discover",
            "hostname": "vc01.example.org",
            "name":     "vm01.example.org"
        }

    Example client message requesting
    additional properties to be collected:

        {
            "method":   "vm.disk.discover",
            "hostname": "vc01.example.org",
            "name":     "vm01.example.org",
            "properties": [
                "capacity",
                "diskPath",
                "freeSpace"
            ]
        }

    Returns:
        The discovered objects in JSON format

    """
    logger.debug(
        '[%s] Discovering guest disks for VirtualMachine %s',
        agent.host,
        msg['name']
    )

    # Find the VM and get the guest disks
    data = _get_object_properties(
        agent=agent,
        properties=['name', 'guest.disk'],
        obj_type=pyVmomi.vim.VirtualMachine,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

    if data['success'] != 0:
        return data

    # Get the VM name and guest disk properties from the result
    props = data['result'][0]
    vm_name, vm_disks = props['name'], props['guest.disk']

    # Properties to be collected for the guest disks
    properties = ['diskPath']
    if 'properties' in msg and msg['properties']:
        properties.extend(msg['properties'])

    # Get the requested disk properties
    result = {}
    result['name'] = vm_name
    result['disk'] = [{prop: getattr(disk, prop, '(null)') for prop in properties} for disk in vm_disks]

    r = {
        'success': 0,
        'msg': 'Successfully discovered objects',
        'result': [result],
    }

    return r

@task(name='vm.guest.net.get', required=['name'])
def vm_guest_net_get(agent, msg):
    """
    Discover network adapters for a vim.VirtualMachine  object

    Note, that this request requires you to have
    VMware Tools installed in order get information about the
    guest network adapters.

    Example client message would be:

        {
            "method":   "vm.guest.net.get",
            "hostname": "vc01.example.org",
            "name":     "vm01.example.org"
        }

    Example client message requesting
    additional properties to be collected:

        {
            "method":   "vm.guest.net.get",
            "hostname": "vc01.example.org",
            "name":     "vm01.example.org",
            "properties": [
                "network",
                "connected",
                "macAddress",
                "ipConfig"
            ]
        }

    Returns:
        The discovered objects in JSON format

    """
    logger.debug(
        '[%s] Discovering network adapters for VirtualMachine %s',
        agent.host,
        msg['name']
    )

    # Find the VM and get the network adapters
    data = _get_object_properties(
        agent=agent,
        properties=['name', 'guest.net'],
        obj_type=pyVmomi.vim.VirtualMachine,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

    if data['success'] != 0:
        return data

    # Get the VM name and network adapters
    # properties from the result
    props = data['result'][0]
    vm_name, vm_networks = props['name'], props['guest.net']

    # Properties to be collected for the guest disks
    properties = ['network']
    if 'properties' in msg and msg['properties']:
        properties.extend(msg['properties'])

    # Get the requested properties
    result = {}
    result['name'] = vm_name
    result['net'] = [{prop: getattr(net, prop, '(null)') for prop in properties} for net in vm_networks]

    r = {
        'success': 0,
        'msg': 'Successfully retrieved properties',
        'result': result,
    }

    return r

@task(name='vm.net.get', required=['name'])
def vm_net_get(agent, msg):
    """
    Get all Networks used by a vim.VirtualMachine managed object

    Example client message would be:

        {
            "method":     "vm.net.get",
            "hostname":   "vc01.example.org",
            "name":       "vm01.example.org",
        }

    Returns:
        The managed object properties in JSON format

    """
    logger.debug(
        '[%s] Getting Networks available for %s VirtualMachine',
        agent.host,
        msg['name']
    )

    # Find the VirtualMachine managed object and
    # get the 'network' property
    data = _get_object_properties(
        agent=agent,
        properties=['name', 'network'],
        obj_type=pyVmomi.vim.VirtualMachine,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

    if data['success'] != 0:
        return data

    props = data['result'][0]
    vm_name, vm_networks = props['name'], props['network']

    # Create a list view for the Network managed objects
    view_ref = agent.get_list_view(obj=vm_networks)
    result = {}
    result['name'] = vm_name
    result['network'] = agent.collect_properties(
        view_ref=view_ref,
        obj_type=pyVmomi.vim.Network,
        path_set=['name']
    )

    view_ref.DestroyView()

    r = {
        'success': 0,
        'msg': 'Successfully discovered objects',
        'result': result,
    }

    return r

def _get_vm_snapshots(agent, name):
    """
    Gets all snapshots for a vim.VirtualMachine object

    Args:
        agent (VConnector): VConnector instance
        name         (str): Name of the VirtualMachine object

    Returns:
        A dict containing the VirtualMachine snaphots

    """
    logger.info(
        '[%s] Getting snapshots for %s VirtualMachine',
        agent.host,
        name
    )

    obj = agent.get_object_by_property(
        property_name='name',
        property_value=name,
        obj_type=pyVmomi.vim.VirtualMachine
    )

    if not obj:
        return {'success': 1, 'msg': 'Cannot find object: {}'.format(name)}

    if not obj.snapshot:
        return {'success': 1, 'msg': 'No snapshots found for: {}'.format(name)}

    snapshots = []
    for root in obj.snapshot.rootSnapshotList:
        snapshots.append(root)
        for child in root.childSnapshotList:
            snapshots.append(child)

    r = {
        'success': 0,
        'msg': 'Successfully retrieved snapshots',
        'result': snapshots,
    }

    return r

@task(name='vm.snapshot.get', required=['name'])
def vm_snapshot_get(agent, msg):
    """
    Gets all snapshots for a vim.VirtualMachine managed object

    Example client message would be:

        {
            "method":     "vm.snapshot.get",
            "hostname":   "vc01.example.org",
            "name":       "vm01.example.org",
        }

    Returns:
        The discovered snapshots as a JSON object

    """
    data = _get_vm_snapshots(agent, name=msg['name'])
    if data['success'] != 0:
        return data

    result = []
    for snapshot in data['result']:
        s = {
            'createTime': str(snapshot.createTime),
            'description': snapshot.description,
            'id': snapshot.id,
            'name': snapshot.name,
            'quiesced': str(snapshot.quiesced),
            'state': snapshot.state,
        }
        result.append(s)

    r = {
        'success': 0,
        'msg': 'Successfully retrieved snapshots',
        'result': result,
    }

    return r

@task(name='vm.get', required=['name', 'properties'])
def vm_get(agent, msg):
    """
    Get properties for a vim.VirtualMachine managed object

    Example client message would be:

        {
            "method":     "vm.get",
            "hostname":   "vc01.example.org",
            "name":       "vm01.example.org",
            "properties": [
                "name",
                "runtime.powerState"
            ]
        }

    Returns:
        The managed object properties in JSON format

    """
    # Property names to be collected
    properties = ['name']
    if 'properties' in msg and msg['properties']:
        properties.extend(msg['properties'])

    return _get_object_properties(
        agent=agent,
        properties=properties,
        obj_type=pyVmomi.vim.VirtualMachine,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

@task(name='vm.host.get', required=['name'])
def vm_host_get(agent, msg):
    """
    Get the vSphere host where a Virtual Machine is running on

    Example client message would be:

        {
            "method":     "vm.host.get",
            "hostname":   "vc01.example.org",
            "name":       "vm01.example.org",
        }

    Returns:
        The managed object properties in JSON format

    """
    logger.debug(
        '[%s] Getting host where %s VirtualMachine is running on',
        agent.host,
        msg['name']
    )

    data = _get_object_properties(
        agent=agent,
        properties=['name', 'runtime.host'],
        obj_type=pyVmomi.vim.VirtualMachine,
        obj_property_name='name',
        obj_property_value=msg['name']
    )

    if data['success'] != 0:
        return data

    props = data['result'][0]
    vm_name, vm_host = props['name'], props['runtime.host']

    result = {
        'name': vm_name,
        'host': vm_host.name,
    }

    r = {
        'success': data['success'],
        'msg': data['msg'],
        'result': [result],
    }

    return r

@task(name='vm.datastore.get', required=['name'])
def vm_datastore_get(agent, msg):
    """
    Get all Datastores used by a vim.VirtualMachine managed object

    Example client message would be:

        {
            "method":   "vm.datastore.get",
            "hostname": "vc01.example.org",
            "name":     "vm01.example.org",
        }

    Returns:
        The discovered objects in JSON format

    """
    return _object_datastore_get(
        agent=agent,
        obj_type=pyVmomi.vim.VirtualMachine,
        name=msg['name']
    )

@task(name='vm.disk.get', required=['name'])
def vm_disk_get(agent, msg):
    """
    Get properties for a disk of a vim.VirtualMachine object

    Note, that this request requires you to have
    VMware Tools installed in order get information about the
    guest disks.

    Example client message would be:

        {
            "method":   "vm.disk.get",
            "hostname": "vc01.example.org",
            "name":     "vm01.example.org"
            "key":      "/var"
        }

    Example client message requesting
    additional properties to be collected:

        {
            "method":   "vm.disk.get",
            "hostname": "vc01.example.org",
            "name":     "vm01.example.org",
            "key":      "/var",
            "properties": [
                "capacity",
                "diskPath",
                "freeSpace"
            ]
        }

    Returns:
        The discovered objects in JSON format

    """
    logger.debug(
        '[%s] Getting guest disk info for %s on VirtualMachine %s',
        agent.host,
        msg['key'],
        msg['name']
    )

    # Discover the VM disks
    data = vm_disk_discover(agent, msg)

    if data['success'] != 0:
        return data

    # If we have no key for the disk,
    # just return the result from discovery
    if 'key' in msg and msg['key']:
        disk_path = msg['key']
    else:
        return data

    props = data['result'][0]
    disks = props['disk']

    for disk in disks:
        if disk['diskPath'] == disk_path:
            break
    else:
        return {
            'success': 1,
            'msg': 'Unable to find guest disk %s' % disk_path
        }

    result = {}
    result['name'] = msg['name']
    result['disk'] = disk

    r = {
        'success': 0,
        'msg': 'Successfully retrieved properties',
        'result': [result],
    }

    return r

@task(name='vm.process.get', required=['name', 'username', 'password'])
def vm_process_get(agent, msg):
    """
    Get processes running on a vim.VirtualMachine managed object

    This method requires you to have VMware Tools installed and
    running in order to get the list of processes running in a
    guest system.

    Example client message would be:

        {
            "method":     "vm.process.get",
            "hostname":   "vc01.example.org",
            "name":       "vm01.example.org",
            "username":   "root",
            "password":   "p4ssw0rd"
        }

    Example client message which requests
    additional properties for the processes:

        {
            "method":     "vm.process.get",
            "hostname":   "vc01.example.org",
            "name":       "vm01.example.org",
            "username":   "root",
            "password":   "p4ssw0rd",
            "properties": [
                "name",
                "owner",
                "pid"
            ]
        }

    Returns:
        The managed object properties in JSON format

    """
    logger.debug(
        '[%s] Getting processes for VirtualMachine %s',
        agent.host,
        msg['name']
    )

    # Get the VirtualMachine managed object
    data = _get_object_properties(
        agent=agent,
        properties=['name', 'guest.toolsRunningStatus'],
        obj_type=pyVmomi.vim.VirtualMachine,
        obj_property_name='name',
        obj_property_value=msg['name'],
        include_mors=True
    )

    if data['success'] != 0:
        return data

    # Get the VM properties
    props = data['result'][0]
    vm_name, vm_tools_is_running, vm_obj = props['name'], props['guest.toolsRunningStatus'], props['obj']

    # Check if we have VMware Tools installed and running first
    # as this request depends on it
    if vm_tools_is_running != 'guestToolsRunning':
        return {
            'success': 1,
            'msg': '%s is not running VMware Tools' % msg['name']
        }

    # Prepare credentials used for
    # authentication in the guest system
    if not msg['username'] or not msg['password']:
        return {'success': 1, 'msg': 'Need username and password for authentication in guest system {}'.format(msg['name'])}

    vm_creds = pyVmomi.vim.vm.guest.NamePasswordAuthentication(
        username=msg['username'],
        password=msg['password']
    )

    try:
        vm_processes = agent.si.content.guestOperationsManager.processManager.ListProcessesInGuest(
            vm=vm_obj,
            auth=vm_creds
        )
    except Exception as e:
        return {
            'success': 1,
            'msg': 'Cannot get guest processes: %s' % e
        }

    # Properties to be collected for the guest processes
    properties = ['cmdLine']
    if 'properties' in msg and msg['properties']:
        properties.extend(msg['properties'])

    # Get the requested process properties
    result = [{prop: getattr(process, prop, '(null)') for prop in properties} for process in vm_processes]

    r = {
        'success': 0,
        'msg': 'Successfully retrieved properties',
        'result': result,
    }

    return r

@task(name='vm.cpu.usage.percent', required=['name'])
def vm_cpu_usage_percent(agent, msg):
    """
    Get the CPU usage in percentage for a VirtualMachine

    NOTE: This task will be gone after the transition to performance counters

    Example client message would be:

        {
            "method":     "vm.cpu.usage.percent",
            "hostname":   "vc01.example.org",
            "name":       "vm01.example.org",
        }

    Returns:
        The managed object properties in JSON format

    """
    logger.debug(
        '[%s] Getting CPU usage percentage for VirtualMachine %s',
        agent.host,
        msg['name']
    )

    # Get the VirtualMachine managed object and collect the
    # properties required to calculate the CPU usage percentage.
    # The CPU usage in percentage is directly related to the
    # host the where the Virtual Machine is running on,
    # so we need to collect the 'runtime.host' property as well.
    required_properties = [
        'name',
        'runtime.host',
        'summary.quickStats.overallCpuUsage',
        'config.hardware.numCoresPerSocket',
        'config.hardware.numCPU',
    ]

    data = _get_object_properties(
        agent=agent,
        properties=required_properties,
        obj_type=pyVmomi.vim.VirtualMachine,
        obj_property_name='name',
        obj_property_value=msg['name'],
    )

    if data['success'] != 0:
        return data

    # Get the VM properties
    props = data['result'][0]

    # TODO: A fix for VMware vSphere 4.x versions, where not
    #       always the properties requested are returned by the
    #       vCenter server, which could result in a KeyError
    #       exception. See this issue for more details:
    #
    #           - https://github.com/dnaeon/py-vpoller/issues/33
    #
    #       We should ensure that vPoller Workers do not fail
    #       under such circumstances and return an error message.
    if not all(p in props for p in required_properties):
        return {
            'success': 1,
            'msg': 'Unable to retrieve required properties'
        }

    # Calculate CPU usage in percentage
    # The overall CPU usage returned by vSphere is in MHz, so
    # we first convert it back to Hz and then calculate percentage
    cpu_usage = (
        float(props['summary.quickStats.overallCpuUsage'] * 1048576) /
        (props['runtime.host'].hardware.cpuInfo.hz * props['config.hardware.numCoresPerSocket'] *
         props['config.hardware.numCPU']) *
        100
    )

    result = {
        'name': props['name'],
        'vm.cpu.usage.percent': cpu_usage
    }

    r = {
        'success': 0,
        'msg': 'Successfully retrieved properties',
        'result': [result],
    }

    return r

@task(name='datastore.discover')
def datastore_discover(agent, msg):
    """
    Discover all pyVmomi.vim.Datastore managed objects

    Example client message would be:

        {
            "method":   "datastore.discover",
            "hostname": "vc01.example.org",
        }

    Example client message which also requests
    additional properties:

        {
            "method":     "datastore.discover",
            "hostname":   "vc01.example.org",
            "properties": [
                "name",
                "summary.url"
            ]
        }

    Returns:
        The discovered objects in JSON format

    """
    # Property names to be collected
    properties = ['name']
    if 'properties' in msg and msg['properties']:
        properties.extend(msg['properties'])

    r = _discover_objects(
        agent=agent,
        properties=properties,
        obj_type=pyVmomi.vim.Datastore
    )

    return r

@task(name='datastore.get', required=['name', 'properties'])
def datastore_get(agent, msg):
    """
    Get properties for a vim.Datastore managed object

    Example client message would be:

        {
            "method":     "datastore.get",
            "hostname":   "vc01.example.org",
            "name":       "ds:///vmfs/volumes/643f118a-a970df28/",
            "properties": [
                "name",
                "summary.accessible",
                "summary.capacity"
            ]
        }

    Returns:
        The managed object properties in JSON format

    """
    # Property names to be collected
    properties = ['name', 'info.url']
    if 'properties' in msg and msg['properties']:
        properties.extend(msg['properties'])

    return _get_object_properties(
        agent=agent,
        properties=properties,
        obj_type=pyVmomi.vim.Datastore,
        obj_property_name='info.url',
        obj_property_value=msg['name']
    )

@task(name='datastore.alarm.get', required=['name'])
def datastore_alarm_get(agent, msg):
    """
    Get all alarms for a vim.Datastore managed object

    Example client message would be:

        {
            "method":   "datastore.alarm.get",
            "hostname": "vc01.example.org",
            "name":     "ds:///vmfs/volumes/643f118a-a970df28/"
        }

    Returns:
        The discovered alarms in JSON format

    """
    result = _object_alarm_get(
        agent=agent,
        obj_type=pyVmomi.vim.Datastore,
        obj_property_name='info.url',
        obj_property_value=msg['name']
    )

    return result

@task(name='datastore.host.get', required=['name'])
def datastore_host_get(agent, msg):
    """
    Get all HostSystem objects attached to a specific Datastore

    Example client message would be:

        {
            "method":     "datastore.host.get",
            "hostname":   "vc01.example.org",
            "name":       "ds:///vmfs/volumes/643f118a-a970df28/",
        }

    """
    logger.info(
        '[%s] Getting HostSystem list using Datastore %s',
        agent.host,
        msg['name']
    )

    # Find the Datastore by it's 'info.url' property
    # and get the HostSystem objects using it
    data = _get_object_properties(
        agent=agent,
        properties=['host'],
        obj_type=pyVmomi.vim.Datastore,
        obj_property_name='info.url',
        obj_property_value=msg['name']
    )

    if data['success'] != 0:
        return data

    # Get properties from the result
    props = data['result'][0]
    obj_host = props['host']

    # obj_host is a list of DatastoreHostMount[] objects,
    # but we need a list of HostSystem ones instead
    obj_host = [h.key for h in obj_host]

    # Get a list view of the hosts from this datastore object
    # and collect their properties
    view_ref = agent.get_list_view(obj=obj_host)
    result = agent.collect_properties(
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

    return r

@task(name='datastore.vm.get', required=['name'])
def datastore_vm_get(agent, msg):
    """
    Get all VirtualMachine objects using a specific Datastore

    Example client message would be:

        {
            "method":     "datastore.vm.get",
            "hostname":   "vc01.example.org",
            "name":       "ds:///vmfs/volumes/643f118a-a970df28/",
        }

    """
    logger.info(
        '[%s] Getting VirtualMachine list using Datastore %s',
        agent.host,
        msg['name']
    )

    # Find the Datastore by it's 'info.url' property and get the
    # VirtualMachine objects using it
    data = _get_object_properties(
        agent=agent,
        properties=['vm'],
        obj_type=pyVmomi.vim.Datastore,
        obj_property_name='info.url',
        obj_property_value=msg['name']
    )

    if data['success'] != 0:
        return data

    # Get properties from the result
    props = data['result'][0]
    obj_vm = props['vm']

    # Get a list view of the VMs from this datastore object
    # and collect their properties
    view_ref = agent.get_list_view(obj=obj_vm)
    result = agent.collect_properties(
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

    return r

@task(name='datastore.perf.metric.info', required=['name'])
def datastore_perf_metric_info(agent, msg):
    """
    Get performance counters available for a vim.Datastore object

    Example client message would be:

        {
            "method":       "datastore.perf.metric.info",
            "hostname":     "vc01.example.org",
            "name":         "ds:///vmfs/volumes/643f118a-a970df28/",
            "counter-name": <counter-id>
        }

    Returns:
        Information about the supported performance counters for the object

    """
    obj = agent.get_object_by_property(
        property_name='info.url',
        property_value=msg['name'],
        obj_type=pyVmomi.vim.Datastore
    )

    if not obj:
        return {'success': 1, 'msg': 'Cannot find object {}'.format(msg['name'])}

    counter_name = msg.get('counter-name')

    return _entity_perf_metric_info(
        agent=agent,
        entity=obj,
        counter_name=counter_name
    )

@task(name='datastore.perf.metric.get', required=['name', 'counter-name'])
def datastore_perf_metric_get(agent, msg):
    """
    Get performance metrics for a vim.Datastore managed object

    The properties passed in the message are the performance
    counter IDs to be retrieved.

    Example client message would be:

        {
            "method":     "datastore.perf.metric.get",
            "hostname":   "vc01.example.org",
            "name":       "ds:///vmfs/volumes/643f118a-a970df28/",
            "counter-id": "datastore.numberReadAveraged.number"
        }

    For historical performance statistics make sure to pass the
    performance interval as part of the message, e.g.:

        {
            "method":   "datastore.perf.metric.get",
            "hostname": "vc01.example.org",
            "name":     "ds:///vmfs/volumes/643f118a-a970df28/",
            "properties": "datastore.numberReadAveraged.number",
            "perf-interval": "Past day"
        }

    Returns:
        The retrieved performance metrics

    """
    obj = agent.get_object_by_property(
        property_name='info.url',
        property_value=msg['name'],
        obj_type=pyVmomi.vim.Datastore
    )

    if not obj:
        return {'success': 1, 'msg': 'Cannot find object: {}'.format(msg['name'])}

    try:
        counter_name = msg.get('counter-name')
        max_sample = int(msg.get('max-sample')) if msg.get('max-sample') else 1
        interval_name = msg.get('perf-interval')
        instance = msg.get('instance') if msg.get('instance') else ''
    except (TypeError, ValueError):
        logger.warning('Invalid message, cannot retrieve performance metrics')
        return {
            'success': 1,
            'msg': 'Invalid message, cannot retrieve performance metrics'
        }

    return _entity_perf_metric_get(
        agent=agent,
        entity=obj,
        counter_name=counter_name,
        max_sample=max_sample,
        instance=instance,
        interval_name=interval_name
    )

@task(name='vsan.health.get', required=['name'])
def vsan_health_get(agent, msg):
    """
    Get VSAN health state for a host

    Example client message would be:

        {
            "method":       "vsan.health.get",
            "hostname":     "vc01.example.org",
            "name":         "esxi01.example.org"
        }

    Returns:
        VSAN health state for the host

    """
    logger.info(
        '[%s] Retrieving VSAN health state for %s',
        agent.host,
        msg['name'],
    )

    properties = [
        'name',
        'runtime.powerState',
        'runtime.connectionState'
    ]

    data = _get_object_properties(
        agent=agent,
        properties=properties,
        obj_type=pyVmomi.vim.HostSystem,
        obj_property_name='name',
        obj_property_value=msg['name'],
        include_mors=True
    )

    if data['success'] != 0:
        return data

    result = data['result'][0]
    if result['runtime.powerState'] != pyVmomi.vim.HostSystemPowerState.poweredOn:
        return {'success': 1, 'msg': 'Host is not powered on, cannot get VSAN health state'}

    if result['runtime.connectionState'] != pyVmomi.vim.HostSystemConnectionState.connected:
        return {'success': 1, 'msg': 'Host is not connected, cannot get VSAN health state'}

    obj = result['obj']
    status = obj.configManager.vsanSystem.QueryHostStatus()
    health = {
        'name': obj.name,
        'uuid': status.uuid,
        'nodeUuid': status.nodeUuid,
        'health': status.health,
    }

    result = {
        'success': 0,
        'msg': 'Successfully retrieved object properties',
        'result': [health],
    }

    return result
