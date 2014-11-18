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

from functools import wraps

from vconnector.core import VConnector
from vpoller.client.core import VPollerClientMessage

__all__ = ['VSphereAgent', 'task']

class VSphereAgent(VConnector):
    """
    VSphereAgent class

    Defines methods for retrieving vSphere object properties

    These are the worker agents that do the actual
    polling from the VMware vSphere host.

    Extends:
        VConnector

    """
    _tasks = {}

    @classmethod
    def _add_task(cls, name, function, required):
        cls._tasks[name] = {
            'function': function,
            'required': required,
        }

    def call_task(self, name, *args, **kwargs):
        """
        Execute a vPoller task request

        Args:
            name (str): Name of the task to be executed

        """
        if name not in self._tasks:
            return {'success': 1, 'msg': 'Unknown task requested'}
        
        return self._tasks[name]['function'](self, *args, **kwargs)

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


def task(name, required):
    """
    Decorator for creating new vPoller tasks

    Args:
        name      (str): Name of the vPoller task
        required (list): A list of required message attributes

    """
    def decorator(function):
        logging.debug(
            'Creating task %s at %s, requiring %s',
            name,
            function,
            required
        )
        @wraps(function)
        def wrapper(*args, **kwargs):
            agent, msg = args
            if not VPollerClientMessage.validate_msg(required, msg):
                return {'success': 1, 'msg': 'Incorrect task request received'}
            
            return function(*args, **kwargs)

        VSphereAgent._add_task(
            name=name,
            function=wrapper,
            required=required
        )
        return wrapper
    return decorator
