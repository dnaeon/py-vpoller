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
vPoller Agent module for the VMware vSphere Poller

vPoller Agents are used by the vPoller Workers, which take care of
establishing the connection to the vSphere hosts and do all the heavy lifting.

Check the vSphere Web Services SDK API for more information on the properties
you can request for any specific vSphere managed object

    - https://www.vmware.com/support/developer/vc-sdk/

"""

import types
import logging

import pyVmomi
from vconnector.core import VConnector


class VSphereAgent(VConnector):
    """
    VSphereAgent class

    Defines methods for retrieving vSphere object properties

    These are the worker agents that do the actual
    polling from the VMware vSphere host.

    Extends:
        VConnector

    """
    def __init__(self, user, pwd, host):
        """
        Initialize a new vSphere Agent

        """
        super(VSphereAgent, self).__init__(user, pwd, host)

        # Message attribute types we expect to receive
        # before we start processing a task request
        self.msg_attr_types = {
            'hostname': (types.StringType, types.UnicodeType),
            'name': (types.StringType, types.UnicodeType, types.NoneType),
            'key': (types.StringType, types.UnicodeType, types.NoneType),
            'username': (types.StringType, types.UnicodeType, types.NoneType),
            'password': (types.StringType, types.UnicodeType, types.NoneType),
            'properties': (types.TupleType,  types.ListType, types.NoneType),
        }

        # Supported vSphere Agent methods where the
        # 'method' key is a reference to the actual method
        # which will be called and 'required' is a list of
        # required message attributes that a client task
        # must provide during the call
        self.agent_methods = {
            'about': {
                'method': self.about,
                'required': ['hostname'],
            },
            'event.latest': {
                'method': self.event_latest,
                'required': ['hostname'],
            },
            'session.get': {
                'method': self.session_get,
                'required': ['hostname'],
            },
            'net.discover': {
                'method': self.net_discover,
                'required': ['hostname'],
            },
            'net.get': {
                'method': self.net_get,
                'required': ['hostname', 'name'],
            },
            'net.host.get': {
                'method': self.net_host_get,
                'required': ['hostname', 'name'],
            },
            'net.vm.get': {
                'method': self.net_vm_get,
                'required': ['hostname', 'name'],
            },
            'datacenter.discover': {
                'method': self.datacenter_discover,
                'required': ['hostname'],
            },
            'datacenter.get': {
                'method': self.datacenter_get,
                'required': ['hostname', 'name', 'properties'],
            },
            'datacenter.perf.metric.get': {
                'method': self.datacenter_perf_metric_get,
                'required': ['hostname', 'name', 'properties'],
            },
            'datacenter.perf.metric.info': {
                'method': self.datacenter_perf_metric_info,
                'required': ['hostname', 'name'],
            },
            'datacenter.alarm.get': {
                'method': self.datacenter_alarm_get,
                'required': ['hostname', 'name'],
            },
            'cluster.perf.metric.get': {
                'method': self.cluster_perf_metric_get,
                'required': ['hostname', 'name', 'properties'],
            },
            'cluster.perf.metric.info': {
                'method': self.cluster_perf_metric_info,
                'required': ['hostname', 'name'],
            },
            'cluster.discover': {
                'method': self.cluster_discover,
                'required': ['hostname'],
            },
            'cluster.get': {
                'method': self.cluster_get,
                'required': ['hostname', 'name', 'properties'],
            },
            'cluster.alarm.get': {
                'method': self.cluster_alarm_get,
                'required': ['hostname', 'name'],
            },
            'resource.pool.discover': {
                'method': self.resource_pool_discover,
                'required': ['hostname'],
            },
            'resource.pool.get': {
                'method': self.resource_pool_get,
                'required': ['hostname', 'name', 'properties'],
            },
            'host.perf.metric.get': {
                'method': self.host_perf_metric_get,
                'required': ['hostname', 'name', 'properties'],
            },
            'host.perf.metric.info': {
                'method': self.host_perf_metric_info,
                'required': ['hostname', 'name'],
            },
            'host.discover': {
                'method': self.host_discover,
                'required': ['hostname'],
            },
            'host.alarm.get': {
                'method': self.host_alarm_get,
                'required': ['hostname', 'name']
            },
            'host.get': {
                'method': self.host_get,
                'required': ['hostname', 'name', 'properties'],
            },
            'host.cluster.get': {
                'method': self.host_cluster_get,
                'required': ['hostname', 'name'],
            },
            'host.vm.get': {
                'method': self.host_vm_get,
                'required': ['hostname', 'name'],
            },
            'host.datastore.get': {
                'method': self.host_datastore_get,
                'required': ['hostname'],
            },
            'host.net.get': {
                'method': self.host_net_get,
                'required': ['hostname', 'name'],
            },
            'vm.alarm.get': {
                'method': self.vm_alarm_get,
                'required': ['hostname', 'name'],
            },
            'vm.discover': {
                'method': self.vm_discover,
                'required': ['hostname'],
            },
            'vm.disk.discover': {
                'method': self.vm_disk_discover,
                'required': ['hostname', 'name'],
            },
            'vm.get': {
                'method': self.vm_get,
                'required': ['hostname', 'name', 'properties'],
            },
            'vm.datastore.get': {
                'method': self.vm_datastore_get,
                'required': ['hostname', 'name'],
            },
            'vm.disk.get': {
                'method': self.vm_disk_get,
                'required': ['hostname', 'name', 'key'],
            },
            'vm.host.get': {
                'method': self.vm_host_get,
                'required': ['hostname', 'name'],
            },
            'vm.guest.net.get': {
                'method': self.vm_guest_net_get,
                'required': ['hostname', 'name'],
            },
            'vm.net.get': {
                'method': self.vm_net_get,
                'required': ['hostname', 'name'],
            },
            'vm.perf.metric.get': {
                'method': self.vm_perf_metric_get,
                'required': ['hostname', 'name', 'properties'],
            },
            'vm.perf.metric.info': {
                'method': self.vm_perf_metric_info,
                'required': ['hostname', 'name'],
            },
            'vm.process.get': {
                'method': self.vm_process_get,
                'required': ['hostname', 'name', 'username', 'password'],
            },
            'vm.cpu.usage.percent': {
                'method': self.vm_cpu_usage_percent,
                'required': ['hostname', 'name'],
            },
            'datastore.discover': {
                'method': self.datastore_discover,
                'required': ['hostname'],
            },
            'datastore.get': {
                'method': self.datastore_get,
                'required': ['hostname', 'name', 'properties'],
            },
            'datastore.alarm.get': {
                'method': self.datastore_alarm_get,
                'required': ['hostname', 'name'],
            },
            'datastore.host.get': {
                'method': self.datastore_host_get,
                'required': ['hostname', 'name'],
            },
            'datastore.vm.get': {
                'method': self.datastore_vm_get,
                'required': ['hostname', 'name'],
            },
            'datastore.perf.metric.info': {
                'method': self.datastore_perf_metric_info,
                'required': ['hostname', 'name'],
            },
            'perf.metric.info': {
                'method': self.perf_metric_info,
                'required': ['hostname'],
            },
            'perf.interval.info': {
                'method': self.perf_interval_info,
                'required': ['hostname'],
            },
        }

    def _validate_client_msg(self, msg, required):
        """
        Helper method for validating a client message

        Checks whether the required attributes are contained
        within the received task request and also checks whether
        they are from the proper type.

        Returns:
            True if the message has been successfully validated,
            False otherwise

        """
        logging.debug(
            'Validating client message, required to have: %s',
            required
        )

        # Check if we have the required message attributes
        if not all(k in msg for k in required):
            logging.debug('Required message attributes are missing')
            return False

        # Check if we have correct types of the message attributes
        for k in msg.keys():
            if k not in self.msg_attr_types:
                continue
            if not isinstance(msg[k], self.msg_attr_types.get(k)):
                logging.debug("Incorrect type for '%s' message attribute", k)
                return False

        logging.debug('Client message successfully validated')

        return True

    def _discover_objects(self, properties, obj_type):
        """
        Helper method to simplify discovery of vSphere managed objects

        This method is used by the '*.discover' vPoller Worker methods and is
        meant for collecting properties for multiple objects at once, e.g.
        during object discovery operation.

        Args:
            properties          (list): List of properties to be collected
            obj_type   (pyVmomi.vim.*): Type of vSphere managed object

        Returns:
            The discovered objects in JSON format

        """
        logging.info(
            '[%s] Discovering %s managed objects',
            self.host,
            obj_type.__name__
        )

        view_ref = self.get_container_view(obj_type=[obj_type])
        try:
            data = self.collect_properties(
                view_ref=view_ref,
                obj_type=obj_type,
                path_set=properties
            )
        except Exception as e:
            return {'success': 1, 'msg': 'Cannot collect properties: %s' % e}

        view_ref.DestroyView()

        result = {
            'success': 0,
            'msg': 'Successfully discovered objects',
            'result': data,
        }

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            result
        )

        return result

    def _get_object_properties(self,
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
            properties             (list): List of properties to be collected
            obj_type       pyVmomi.vim.*): Type of vSphere managed object
            obj_property_name       (str): Property name used for searching for the object
            obj_property_value      (str): Property value identifying the object in question

        Returns:
            The collected properties for this managed object in JSON format

        """
        logging.info(
            '[%s] Retrieving properties for %s managed object of type %s',
            self.host,
            obj_property_value,
            obj_type.__name__
        )

        # Find the Managed Object reference for the requested object
        try:
            obj = self.get_object_by_property(
                property_name=obj_property_name,
                property_value=obj_property_value,
                obj_type=obj_type
            )
        except Exception as e:
            return {'success': 1, 'msg': 'Cannot collect properties: %s' % e}

        if not obj:
            return {
                'success': 1,
                'msg': 'Cannot find object %s' % obj_property_value
            }

        # Create a list view for this object and collect properties
        view_ref = self.get_list_view(obj=[obj])

        try:
            data = self.collect_properties(
                view_ref=view_ref,
                obj_type=obj_type,
                path_set=properties,
                include_mors=include_mors
            )
        except Exception as e:
            return {'success': 1, 'msg': 'Cannot collect properties: %s' % e}

        view_ref.DestroyView()

        result = {
            'success': 0,
            'msg': 'Successfully retrieved object properties',
            'result': data,
        }

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            result
        )

        return result

    def _object_datastore_get(self, obj_type, name):
        """
        Helper method used for getting the datastores available to an object

        This method searches for the managed object with 'name' and retrieves
        the 'datastore' property which contains all datastores available/used
        by the managed object, e.g. VirtualMachine, HostSystem.

        Args:
            obj_type (pyVmomi.vim.*): Managed object type
            name               (str): Name of the managed object, e.g. host, vm

        Returns:
            The discovered objects in JSON format

        """
        logging.debug(
            '[%s] Getting datastores for %s managed object of type %s',
            self.host,
            name,
            obj_type.__name__
        )

        # Find the object by it's 'name' property
        # and get the datastores available/used by it
        data = self._get_object_properties(
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
        view_ref = self.get_list_view(obj=obj_datastores)
        result = self.collect_properties(
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

        logging.debug('[%s] Returning result from operation: %s', self.host, r)

        return r

    def _object_alarm_get(self,
                          obj_type,
                          obj_property_name,
                          obj_property_value):
        """
        Helper method for retrieving alarms for a single Managed Object

        Args:
            obj_type      (pyVmomi.vim.*): Type of the Managed Object
            obj_property_name       (str): Property name used for searching for the object
            obj_property_value      (str): Property value identifying the object in question

        Returns:
            The triggered alarms for the Managed Object

        """
        logging.debug(
            '[%s] Retrieving alarms for %s managed object of type %s',
            self.host,
            obj_property_value,
            obj_type.__name__
        )

        # Get the 'triggeredAlarmState' property for the managed object
        data = self._get_object_properties(
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

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            r
        )

        return r

    def _entity_perf_metric_info(self, entity):
        """
        Get info about supported performance metrics for a managed entity

        If the managed entity supports real-time statistics then
        return the real-time performance counters available for it,
        otherwise fall back to historical statistics only.

        Args:
            entity (pyVmomi.vim.*): A managed entity to lookup

        Returns:
            Information about supported performance metrics for the entity

        """
        if not isinstance(entity, pyVmomi.vim.ManagedEntity):
            return {'success': 0, 'msg': '%s is not a managed entity' % entity}

        provider_summary = self.si.content.perfManager.QueryPerfProviderSummary(
            entity=entity
        )

        if provider_summary.currentSupported:
            logging.info('[%s]: Entity %s supports real-time statistics', self.host, entity.name)
            interval_id = provider_summary.refreshRate
        else:
            logging.info('[%s]: Entity %s supports historical statistics only', self.host, entity.name)
            interval_id = None

        try:
            metric_id = self.si.content.perfManager.QueryAvailablePerfMetric(
                entity=entity,
                intervalId=interval_id
            )
        except pyVmomi.vim.InvalidArgument as e:
            return {
                'success': 1,
                'msg': 'Cannot retrieve performance metrics for %s: %s' % (entity.name, e)
            }

        data = [{k: getattr(m, k) for k in ('counterId', 'instance')} for m in metric_id]
        result = {
            'msg': 'Successfully retrieved performance metrics',
            'success': 0,
            'result': data
        }

        return result

    def _entity_perf_metric_get(self, entity, counter_id, max_sample=1, instance="", interval_key=None):
        """
        Retrieve performance metrics from a managed object

        Args:
            entity     (pyVmomi.vim.*): A managed object
            counter_id          (list): A list of counter IDs to retrieve
            max_sample           (int): Max samples to be retrieved
            instance             (str): Instance name, e.g. vmnic0
            interval_key         (int): Key of historical performance interval to use

        Returns:
            The collected performance metrics from the managed object

        """
        logging.info(
            '[%s] Retrieving performance metrics for %s: %s',
            self.host,
            entity.name,
            counter_id
        )

        # Get the available performance metrics for this managed object
        try:
            metric_id = self.si.content.perfManager.QueryAvailablePerfMetric(entity=entity)
        except pyVmomi.vim.InvalidArgument as e:
            return {
                'success': 1,
                'msg': 'Cannot retrieve performance metrics for %s: %s' % (msg['name'], e)
            }

        # Check whether the object supports real-time statistics
        # If the entity does not support real-time statistics then
        # we fall back to historical stats only.
        # For historical statistics we require a valid performance
        # interval key to be provided
        historical_interval = self.si.content.perfManager.historicalInterval
        provider_summary = self.si.content.perfManager.QueryPerfProviderSummary(
            entity=entity
        )

        if not provider_summary.currentSupported:
            logging.info('[%s] Entity %s does not support real-time statistics', self.host, entity.name)
            logging.info('[%s] Retrieving historical statistics for entity %s', self.host, entity.name)

        if not provider_summary.currentSupported and not interval_key:
            logging.warning(
                '[%s] Entity %s supports historical statistics only, but no historical interval provided',
                self.host,
                entity.name
            )
            return {'success': 1, 'msg': 'Entity %s supports historical statistics only, but no historical interval provided' % entity.name}

        # For real-time statistics use the refresh rate of the provider.
        # For historical statistics use one of the existing historical
        # intervals on the system.
        # For managed entities that support both real-time and historical
        # statistics in order to retrieve historical stats a valid
        # interval key should be provided.
        if interval_key:
            if interval_key not in [str(i.key) for i in historical_interval]:
                logging.warning(
                    '[%s] Historical interval with key %s does not exist',
                    self.host,
                    interval_key
                )
                return {'success': 1, 'msg': 'Historical interval with key %s does not exist' % interval_key}
            else:
                interval_id = [i for i in historical_interval if str(i.key) == interval_key].pop().samplingPeriod
        else:
            interval_id = provider_summary.refreshRate

        # From the requested performance counters collect only the
        # ones that are available for this managed object
        counter_id = [int(c) for c in counter_id]
        available_counter_id = set([m.counterId for m in metric_id])
        to_collect_counter_id = available_counter_id.intersection(set(counter_id))

        if not to_collect_counter_id:
            return {
                'success': 1,
                'msg': 'Requested performance counters are not available for entity %s' % entity.name,
            }

        to_collect_metric_id = [pyVmomi.vim.PerformanceManager.MetricId(counterId=c_id, instance=instance) for c_id in to_collect_counter_id]

        # Get the metric IDs to collect and build our query spec
        if not max_sample:
            max_sample = 1

        # TODO: Be able to specify interval with startTime and endTime as well
        query_spec = pyVmomi.vim.PerformanceManager.QuerySpec(
            maxSample=max_sample,
            entity=entity,
            metricId=to_collect_metric_id,
            intervalId=interval_id
        )

        # Get the performance metrics and return result
        data = self.si.content.perfManager.QueryPerf(
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
                        'counterId': value.id.counterId,
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

    def event_latest(self, msg):
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
        logging.info('[%s] Retrieving latest registered event', self.host)

        e = self.si.content.eventManager.latestEvent.fullFormattedMessage

        result = {
            'msg': 'Successfully retrieved event',
            'success': 0,
            'result': [{'event': e}],
        }

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            result
        )

        return result

    def about(self, msg):
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
        logging.info("[%s] Retrieving vSphere About information", self.host)

        # If no properties are specified just return the 'fullName' property
        if 'properties' not in msg or not msg['properties']:
            properties = ['fullName']
        else:
            properties = msg['properties']

        about = {prop: getattr(self.si.content.about, prop, '(null)') for prop in properties}
        result = {
            'msg': 'Successfully retrieved properties',
            'success': 0,
            'result': [about],
        }

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            result
        )

        return result

    def session_get(self, msg):
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
        logging.info('[%s] Retrieving established sessions', self.host)

        try:
            sm = self.si.content.sessionManager
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

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            result
        )

        return result

    def perf_metric_info(self, msg):
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
        logging.info(
            '[%s] Retrieving supported performance counters',
            self.host
        )

        counter = self.si.content.perfManager.perfCounter
        counter_id = [c.key for c in counter]

        try:
            counter_info = self.si.content.perfManager.QueryPerfCounter(
                counterId=counter_id
            )
        except Exception as e:
            return {'success': 1, 'msg': 'Cannot retrieve performance counters info: %s' % e}

        data = []
        for c in counter_info:
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
            'msg': 'Successfully retrieved performance counters info',
            'result': data
        }

        return result

    def perf_interval_info(self, msg):
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
        logging.info(
            '[%s] Retrieving existing performance historical intervals',
            self.host
        )

        historical_interval = self.si.content.perfManager.historicalInterval

        data = [{k: getattr(interval, k) for k in ('enabled', 'key', 'length', 'level', 'name', 'samplingPeriod')} for interval in historical_interval]

        result = {
            'msg': 'Successfully retrieved performance historical intervals',
            'success': 0,
            'result': data
        }

        return result

    def net_discover(self, msg):
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

        r = self._discover_objects(
            properties=properties,
            obj_type=pyVmomi.vim.Network
        )

        return r

    def net_get(self, msg):
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

        return self._get_object_properties(
            properties=properties,
            obj_type=pyVmomi.vim.Network,
            obj_property_name='name',
            obj_property_value=msg['name']
        )

    def net_host_get(self, msg):
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
            self.host,
            msg['name']
        )

        # Find the Network managed object and get the 'host' property
        data = self._get_object_properties(
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
        view_ref = self.get_list_view(obj=network_hosts)
        result = {}
        result['name'] = network_name
        result['host'] = self.collect_properties(
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

        logging.debug('[%s] Returning result from operation: %s', self.host, r)

        return r

    def net_vm_get(self, msg):
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
            self.host,
            msg['name']
        )

        # Find the Network managed object and get the 'vm' property
        data = self._get_object_properties(
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
        view_ref = self.get_list_view(obj=network_vms)
        result = {}
        result['name'] = network_name
        result['vm'] = self.collect_properties(
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

        logging.debug('[%s] Returning result from operation: %s', self.host, r)

        return r

    def datacenter_discover(self, msg):
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

        r = self._discover_objects(
            properties=properties,
            obj_type=pyVmomi.vim.Datacenter
        )

        return r


    def datacenter_perf_metric_get(self, msg):
        """
        Get performance metrics for a vim.Datacenter managed object

        The properties passed in the message are the performance
        counter IDs to be retrieved.

        Example client message would be:

            {
                "method":   "datacenter.perf.metric.get",
                "hostname": "vc01.example.org",
                "name":     "MyDatacenter",
                "properties": [
                    256,  # VM power on count
                    257,  # VM power off count
                    258   # VM suspend count
                ],
                "key": 1, # Historical performance interval with key 1 (Past day)
                "max_sample": 1
            }

        Returns:
            The retrieved performance metrics

        """
        obj = self.get_object_by_property(
            property_name='name',
            property_value=msg['name'],
            obj_type=pyVmomi.vim.Datacenter
        )

        if not obj:
            return {'success': 1, 'msg': 'Cannot find object: %s' % msg['name']}

        # Interval ID is passed as the 'key' message attribute
        max_sample, key = msg.get('max_sample'), msg.get('key')
        return self._entity_perf_metric_get(
            entity=obj,
            counter_id=msg['properties'],
            max_sample=max_sample,
            interval_key=key
        )

    def datacenter_perf_metric_info(self, msg):
        """
        Get performance counters available for a vim.Datacenter object

        Example client message would be:

            {
                "method":     "datacenter.perf.metric.info",
                "hostname":   "vc01.example.org",
                "name":       "MyDatacenter"
            }

        Returns:
            Information about the supported performance counters for the object

        """
        obj = self.get_object_by_property(
            property_name='name',
            property_value=msg['name'],
            obj_type=pyVmomi.vim.Datacenter
        )

        if not obj:
            return {'success': 1, 'msg': 'Cannot find object %s' % msg['name'] }

        return self._entity_perf_metric_info(entity=obj)

    def datacenter_get(self, msg):
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

        return self._get_object_properties(
            properties=properties,
            obj_type=pyVmomi.vim.Datacenter,
            obj_property_name='name',
            obj_property_value=msg['name']
        )

    def datacenter_alarm_get(self, msg):
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
        result = self._object_alarm_get(
            obj_type=pyVmomi.vim.Datacenter,
            obj_property_name='name',
            obj_property_value=msg['name']
        )

        return result

    def cluster_discover(self, msg):
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

        r = self._discover_objects(
            properties=properties,
            obj_type=pyVmomi.vim.ClusterComputeResource
        )

        return r

    def cluster_perf_metric_get(self, msg):
        """
        Get performance metrics for a vim.ClusterComputeResource managed object

        The properties passed in the message are the performance
        counter IDs to be retrieved.

        Example client message would be:

            {
                "method":   "cluster.perf.metric.get",
                "hostname": "vc01.example.org",
                "name":     "MyCluster",
                "properties": [
                    276,  # Effective memory resources
                    277   # Total amount of CPU resources of all hosts in the cluster
                ],
                "key": 1, # Historical performance interval key '1' (Past day)
                "max_sample": 1
            }

        Returns:
            The retrieved performance metrics

        """
        obj = self.get_object_by_property(
            property_name='name',
            property_value=msg['name'],
            obj_type=pyVmomi.vim.ClusterComputeResource
        )

        if not obj:
            return {'success': 1, 'msg': 'Cannot find object: %s' % msg['name']}

        # Interval ID is passed as the 'key' message attribute
        max_sample, key = msg.get('max_sample'), msg.get('key')
        return self._entity_perf_metric_get(
            entity=obj,
            counter_id=msg['properties'],
            max_sample=max_sample,
            interval_key=key
        )

    def cluster_perf_metric_info(self, msg):
        """
        Get performance counters available for a vim.ClusterComputeResource object

        Example client message would be:

            {
                "method":     "cluster.perf.metric.info",
                "hostname":   "vc01.example.org",
                "name":       "MyCluster"
            }

        Returns:
            Information about the supported performance counters for the object

        """
        obj = self.get_object_by_property(
            property_name='name',
            property_value=msg['name'],
            obj_type=pyVmomi.vim.ClusterComputeResource
        )

        if not obj:
            return {'success': 1, 'msg': 'Cannot find object %s' % msg['name'] }

        return self._entity_perf_metric_info(entity=obj)

    def cluster_get(self, msg):
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

        return self._get_object_properties(
            properties=properties,
            obj_type=pyVmomi.vim.ClusterComputeResource,
            obj_property_name='name',
            obj_property_value=msg['name']
        )

    def cluster_alarm_get(self, msg):
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
        result = self._object_alarm_get(
            obj_type=pyVmomi.vim.ClusterComputeResource,
            obj_property_name='name',
            obj_property_value=msg['name']
        )

        return result

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

        r = self._discover_objects(
            properties=properties,
            obj_type=pyVmomi.vim.ResourcePool
        )

        return r

    def resource_pool_get(self, msg):
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

        return self._get_object_properties(
            properties=properties,
            obj_type=pyVmomi.vim.ResourcePool,
            obj_property_name='name',
            obj_property_value=msg['name']
        )

    def host_discover(self, msg):
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

        r = self._discover_objects(
            properties=properties,
            obj_type=pyVmomi.vim.HostSystem
        )

        return r

    def host_get(self, msg):
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

        return self._get_object_properties(
            properties=properties,
            obj_type=pyVmomi.vim.HostSystem,
            obj_property_name='name',
            obj_property_value=msg['name']
        )

    def host_alarm_get(self, msg):
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
        result = self._object_alarm_get(
            obj_type=pyVmomi.vim.HostSystem,
            obj_property_name='name',
            obj_property_value=msg['name']
        )

        return result

    def host_perf_metric_get(self, msg):
        """
        Get performance metrics for a vim.HostSystem managed object

        The properties passed in the message are the performance
        counter IDs to be retrieved.

        Example client message would be:

            {
                "method":   "host.perf.metric.get",
                "hostname": "vc01.example.org",
                "name":     "esxi01.example.org",
                "properties": [
                    276,  # Effective memory resources
                    277   # Total amount of CPU resources of all hosts in the cluster
                ],
                "key": 1, # Historical performance interval key '1' (Past day)
                "max_sample": 1
            }

        Returns:
            The retrieved performance metrics

        """
        obj = self.get_object_by_property(
            property_name='name',
            property_value=msg['name'],
            obj_type=pyVmomi.vim.HostSystem
        )

        if not obj:
            return {'success': 1, 'msg': 'Cannot find object: %s' % msg['name']}

        # Interval ID is passed as the 'key' message attribute
        max_sample, key = msg.get('max_sample'), msg.get('key')
        return self._entity_perf_metric_get(
            entity=obj,
            counter_id=msg['properties'],
            max_sample=max_sample,
            interval_key=key
        )

    def host_perf_metric_info(self, msg):
        """
        Get performance counters available for a vim.HostSystem object

        Example client message would be:

            {
                "method":     "host.perf.metric.info",
                "hostname":   "vc01.example.org",
                "name":       "esxi01.example.org",
            }

        Returns:
            Information about the supported performance counters for the object

        """
        obj = self.get_object_by_property(
            property_name='name',
            property_value=msg['name'],
            obj_type=pyVmomi.vim.HostSystem
        )

        if not obj:
            return {'success': 1, 'msg': 'Cannot find object %s' % msg['name'] }

        return self._entity_perf_metric_info(entity=obj)

    def host_cluster_get(self, msg):
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
        logging.debug(
            '[%s] Getting cluster name for %s host',
            self.host,
            msg['name']
        )

        # Find the HostSystem managed object and get the 'parent' property
        data = self._get_object_properties(
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

        logging.debug('[%s] Returning result from operation: %s', self.host, r)

        return r

    def host_vm_get(self, msg):
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
        logging.debug(
            '[%s] Getting VirtualMachine list running on %s host',
            self.host,
            msg['name']
        )

        # Find the HostSystem managed object and get the 'vm' property
        data = self._get_object_properties(
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
        view_ref = self.get_list_view(obj=host_vms)
        result = self.collect_properties(
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

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            r
        )

        return r

    def host_net_get(self, msg):
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
        logging.debug(
            '[%s] Getting Network list available for %s host',
            self.host,
            msg['name']
        )

        # Find the HostSystem managed object
        # and get the 'network' property
        data = self._get_object_properties(
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
        view_ref = self.get_list_view(obj=host_networks)
        result = {}
        result['name'] = host_name
        result['network'] = self.collect_properties(
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

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            r
        )

        return r

    def host_datastore_get(self, msg):
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
        return self._object_datastore_get(
            obj_type=pyVmomi.vim.HostSystem,
            name=msg['name']
        )

    def vm_alarm_get(self, msg):
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
        result = self._object_alarm_get(
            obj_type=pyVmomi.vim.VirtualMachine,
            obj_property_name='name',
            obj_property_value=msg['name']
        )

        return result

    def vm_perf_metric_get(self, msg):
        """
        Get performance metrics for a vim.VirtualMachine managed object

        The properties passed in the message are the performance
        counter IDs to be retrieved.

        Example client message would be:

            {
                "method":   "vm.perf.metric.get",
                "hostname": "vc01.example.org",
                "name":     "vm01.example.org",
                "properties": [
                    12, # CPU Ready time of the Virtual Machine
                ],
                "max_sample": 1,
                "instance": ""
            }

        For historical performance statistics make sure to pass the
        performance interval key as part of the message, e.g.:

            {
                "method":   "vm.perf.metric.get",
                "hostname": "vc01.example.org",
                "name":     "vm01.example.org",
                "properties": [
                    12,  # CPU Ready time of the Virtual Machine
                    24   # Memory usage as percentage of total configured or available memory
                ],
                "key": 1 # Historical performance interval key '1' (Past day)
            }

        Returns:
            The retrieved performance metrics

        """
        obj = self.get_object_by_property(
            property_name='name',
            property_value=msg['name'],
            obj_type=pyVmomi.vim.VirtualMachine
        )

        if not obj:
            return {'success': 1, 'msg': 'Cannot find object: %s' % msg['name']}

        # Interval ID is passed as the 'key' message attribute
        max_sample, key, instance = msg.get('max_sample'), msg.get('key'), msg.get('instance')
        return self._entity_perf_metric_get(
            entity=obj,
            counter_id=msg['properties'],
            max_sample=max_sample,
            interval_key=key,
            instance=instance
        )

    def vm_perf_metric_info(self, msg):
        """
        Get performance counters available for a vim.VirtualMachine object

        Example client message would be:

            {
                "method":     "vm.perf.metric.info",
                "hostname":   "vc01.example.org",
                "name":       "vm01.example.org",
            }

        Returns:
            Information about the supported performance counters for the object

        """
        obj = self.get_object_by_property(
            property_name='name',
            property_value=msg['name'],
            obj_type=pyVmomi.vim.VirtualMachine
        )

        if not obj:
            return {'success': 1, 'msg': 'Cannot find object %s' % msg['name'] }

        return self._entity_perf_metric_info(entity=obj)

    def vm_discover(self, msg):
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

        r = self._discover_objects(
            properties=properties,
            obj_type=pyVmomi.vim.VirtualMachine
        )

        return r

    def vm_disk_discover(self, msg):
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
        logging.debug(
            '[%s] Discovering guest disks for VirtualMachine %s',
            self.host,
            msg['name']
        )

        # Find the VM and get the guest disks
        data = self._get_object_properties(
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

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            r
        )

        return r

    def vm_guest_net_get(self, msg):
        """
        Discover network adapters for a vim.VirtualMachine  object

        Note, that this request requires you to have
        VMware Tools installed in order get information about the
        guest network adapters.

        Example client message would be:

            {
                "method":   "vm.net.discover",
                "hostname": "vc01.example.org",
                "name":     "vm01.example.org"
            }

        Example client message requesting
        additional properties to be collected:

            {
                "method":   "vm.net.discover",
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
        logging.debug(
            '[%s] Discovering network adapters for VirtualMachine %s',
            self.host,
            msg['name']
        )

        # Find the VM and get the network adapters
        data = self._get_object_properties(
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

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            r
        )

        return r

    def vm_net_get(self, msg):
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
        logging.debug(
            '[%s] Getting Networks available for %s VirtualMachine',
            self.host,
            msg['name']
        )

        # Find the VirtualMachine managed object and
        # get the 'network' property
        data = self._get_object_properties(
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
        view_ref = self.get_list_view(obj=vm_networks)
        result = {}
        result['name'] = vm_name
        result['network'] = self.collect_properties(
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

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            r
        )

        return r

    def vm_get(self, msg):
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

        return self._get_object_properties(
            properties=properties,
            obj_type=pyVmomi.vim.VirtualMachine,
            obj_property_name='name',
            obj_property_value=msg['name']
        )

    def vm_host_get(self, msg):
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
        logging.debug(
            '[%s] Getting host where %s VirtualMachine is running on',
            self.host,
            msg['name']
        )

        data = self._get_object_properties(
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

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            r
        )

        return r

    def vm_datastore_get(self, msg):
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
        return self._object_datastore_get(
            obj_type=pyVmomi.vim.VirtualMachine,
            name=msg['name']
        )

    def vm_disk_get(self, msg):
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
        logging.debug(
            '[%s] Getting guest disk info for %s on VirtualMachine %s',
            self.host,
            msg['key'],
            msg['name']
        )

        # Discover the VM disks
        data = self.vm_disk_discover(msg)

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

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            r
        )

        return r

    def vm_process_get(self, msg):
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
        logging.debug(
            '[%s] Getting processes for VirtualMachine %s',
            self.host,
            msg['name']
        )

        # Get the VirtualMachine managed object
        data = self._get_object_properties(
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
            return {'success': 1, 'msg': 'Need username and password for authentication in guest system %s' % msg['name']}

        vm_creds = pyVmomi.vim.vm.guest.NamePasswordAuthentication(
            username=msg['username'],
            password=msg['password']
        )

        try:
            vm_processes = self.si.content.guestOperationsManager.processManager.ListProcessesInGuest(
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

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            r
        )

        return r

    def vm_cpu_usage_percent(self, msg):
        """
        Get the CPU usage in percentage for a VirtualMachine

        Example client message would be:

            {
                "method":     "vm.cpu.usage.percent",
                "hostname":   "vc01.example.org",
                "name":       "vm01.example.org",
            }

        Returns:
            The managed object properties in JSON format

        """
        logging.debug(
            '[%s] Getting CPU usage percentage for VirtualMachine %s',
            self.host,
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

        data = self._get_object_properties(
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

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            r
        )

        return r

    def datastore_discover(self, msg):
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

        r = self._discover_objects(
            properties=properties,
            obj_type=pyVmomi.vim.Datastore
        )

        return r

    def datastore_get(self, msg):
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

        return self._get_object_properties(
            properties=properties,
            obj_type=pyVmomi.vim.Datastore,
            obj_property_name='info.url',
            obj_property_value=msg['name']
        )

    def datastore_alarm_get(self, msg):
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
        result = self._object_alarm_get(
            obj_type=pyVmomi.vim.Datastore,
            obj_property_name='info.url',
            obj_property_value=msg['name']
        )

        return result

    def datastore_host_get(self, msg):
        """
        Get all HostSystem objects attached to a specific Datastore

        Example client message would be:

            {
                "method":     "datastore.host.get",
                "hostname":   "vc01.example.org",
                "name":       "ds:///vmfs/volumes/643f118a-a970df28/",
            }

        """
        logging.info(
            '[%s] Getting HostSystem list using Datastore %s',
            self.host,
            msg['name']
        )

        # Find the Datastore by it's 'info.url' property
        # and get the HostSystem objects using it
        data = self._get_object_properties(
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
        view_ref = self.get_list_view(obj=obj_host)
        result = self.collect_properties(
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

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            r
        )

        return r

    def datastore_vm_get(self, msg):
        """
        Get all VirtualMachine objects using a specific Datastore

        Example client message would be:

            {
                "method":     "datastore.vm.get",
                "hostname":   "vc01.example.org",
                "name":       "ds:///vmfs/volumes/643f118a-a970df28/",
            }

        """
        logging.info(
            '[%s] Getting VirtualMachine list using Datastore %s',
            self.host,
            msg['name']
        )

        # Find the Datastore by it's 'info.url' property and get the
        # VirtualMachine objects using it
        data = self._get_object_properties(
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
        view_ref = self.get_list_view(obj=obj_vm)
        result = self.collect_properties(
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

        logging.debug(
            '[%s] Returning result from operation: %s',
            self.host,
            r
        )

        return r

    def datastore_perf_metric_info(self, msg):
        """
        Get performance counters available for a vim.Datastore object

        Example client message would be:

            {
                "method":     "datastore.perf.metric.info",
                "hostname":   "vc01.example.org",
                "name":       "ds:///vmfs/volumes/643f118a-a970df28/",
            }

        Returns:
            Information about the supported performance counters for the object

        """
        obj = self.get_object_by_property(
            property_name='info.url',
            property_value=msg['name'],
            obj_type=pyVmomi.vim.Datastore
        )

        if not obj:
            return {'success': 1, 'msg': 'Cannot find object %s' % msg['name'] }

        return self._entity_perf_metric_info(entity=obj)
