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
Core module for the VMware vSphere Poller

The principal work of the vPoller system can be seen in the diagram below.

The diagram shows clients sending ZeroMQ messages to a ZeroMQ proxy,
which load balances client requests between two workers.

   		    +---------+   +---------+   +---------+
    		    |  Client |   |  Client |   |  Client |
                    +---------+   +---------+   +---------+
                    |   REQ   |   |   REQ   |   |   REQ   |
                    +---------+   +---------+   +---------+
                         |             |             |
                         +-------------+-------------+
                                       |
                                       | 
                                       |
                                  +---------+
                                  |  ROUTER | -> Socket facing clients
                                  +---------+
                                  |  Proxy  | -> Load Balancer (ZeroMQ Broker)
                                  +---------+
                                  |   Mgmt  | -> Management socket
                                  +---------+
                                  |  DEALER | -> Socket to which workers connect
                                  +---------+
                                       |
                                       | 
                                       |
                   +-------------------+-------------------+     
                   |                                       |
              +---------+                             +---------+
              |  DEALER |		     	      |  DEALER | -> Worker socket connecting to the Proxy
              +---------+			      +---------+
              |   Mgmt  |                             |   Mgmt  | -> Management socket
              +---------+                             +---------+
              |  Worker |			      |  Worker | -> Worker process
              +---------+			      +---------+
                   |                                       |
                   +-------------------+-------------------+
                                       |
                     +---------------- +----------------+
                     |                 |                |
              +-------------+   +-------------+   +-------------+
              | vSphere API |   | vSphere API |   | vSphere API |
              +-------------+   +-------------+   +-------------+
              |   vSphere   |   |   vSphere   |   |   vSphere   |
              +-------------+   +-------------+   +-------------+
              |  ESX Hosts  |   |  ESX Hosts  |   |  ESX Hosts  |
              +-------------+   +-------------+   +-------------+
              |  Datastores |   |  Datastores |   |  Datastores |
              +-------------+   +-------------+   +-------------+

"""   

from threading import Timer

class VPollerException(Exception):
    """
    Generic VPoller exception.

    """
    pass

class VPollerPeriodTask(object):
    """
    Perform period tasks at a given interval

    """
    def __init__(self, interval, daemon=True, callback, **kwargs):
        self.interval = interval
        self.daemon = daemon
        self.callback = callback
        self.kwargs = kwargs

    def run(self):
        self.callback(**self.kwargs)
        t = Timer(self.interval, self.run)
        t.daemon = self.daemon
        t.start()
