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
vPoller Registry module

"""

from vpoller.exceptions import VPollerException
from vpoller.task.core import Task

__all__ = ['TaskRegistry']


class TaskRegistry(object):
    """
    A registry for the vPoller tasks

    """
    def __init__(self):
        self._registry = {}

    def __contains__(self, item):
        return item in self._registry

    def register(self, task):
        """
        Register a new task

        Args:
            task (Task): A Task instance to be registered

        """
        if not isinstance(task, Task):
            raise VPollerException('The task should be an instance of Task class')

        self._registry[task.name] = task

    def unregister(self, name):
        """
        Removes a task from the registry

        Args:
            name (str): Name of the task to remove from registry

        """
        self._registry.pop(name)

    def get(self, name):
        """
        Get a task by name

        """
        return self._registry.get(name)


registry = TaskRegistry()
