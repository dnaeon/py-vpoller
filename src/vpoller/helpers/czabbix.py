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
vPoller Zabbix Helper module for C clients

The vPoller Zabbix Helper module for C clients provides routines for
translating a result vPoller message to a Zabbix-friendly format.

This module is to be used by vPoller C clients only.

"""

import vpoller.helpers.zabbix


class HelperAgent(object):
    """
    HelperAgent class of the Zabbix vPoller Helper for C clients

    """
    def __init__(self, msg, data):
        """
        Initializes a new HelperAgent object

        Args:
            msg  (dict): The original request message
            data (dict): The data to be processed by the helper

        """
        self.msg = msg
        self.data = data

    def run(self):
        """
        Main Helper method

        Invokes the vpoller.helpers.zabbix helper for processing
        any data to Zabbix format and NULL-terminates the data, so
        that C clients can properly get the data we send to them.

        """
        helper = vpoller.helpers.zabbix.HelperAgent(
            msg=self.msg,
            data=self.data
        )

        result = helper.run()

        return result + '\0'
