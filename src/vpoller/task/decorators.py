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
vPoller Task Decorators module

"""

from functools import wraps
from traceback import format_exc

from vpoller.log import logger
from vpoller.task.core import Task
from vpoller.task.registry import registry

__all__ = ['task']


def task(name, required=None):
    """
    A decorator for creating new tasks

    Args:
        name      (str): Name of the task
        required (list): A list of required message keys
                         that the task expects to be present

    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            logger.debug('Executing task %s', name)
            try:
                result = fn(*args, **kwargs)
            except Exception as e:
                tb = format_exc()
                result = {
                    'success': 1,
                    'msg': 'Task {} failed'.format(name),
                    'traceback': tb
                }
                logger.warning('Task %s failed: %s', name, tb)
            finally:
                logger.debug('Returning result from task %s: %s', name, result)
                return result
        t = Task(name=name, function=wrapper, required=required)
        registry.register(t)
        return wrapper
    return decorator
