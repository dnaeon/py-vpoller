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
vPoller CSV Helper module

The vPoller CSV Helper module provides routines for
translating a result vPoller message to CSV format.

"""

import csv
import json
import cStringIO


class HelperAgent(object):
    """
    HelperAgent class of the CSV vPoller Helper

    """
    def __init__(self, msg, data):
        """
        Initializes a new HelperAgent object

        Args:
            msg  (dict): The original request message
            data  (str): The result message data

        """
        self.msg = msg
        self.data = data

    def run(self):
        """
        Main Helper method

        Processes the data and does any translations if needed

        """
        # Check whether the request was successful first
        if self.data['success'] != 0:
            return json.dumps(self.data, indent=4)

        data = self.data['result']
        result = cStringIO.StringIO()
        headers = sorted(data[0].keys())

        writer = csv.DictWriter(
            result,
            headers,
            restval='None',
            extrasaction='ignore',
            quotechar='"'
        )
        writer.writeheader()

        for item in data:
            writer.writerow(item)

        return result.getvalue()
