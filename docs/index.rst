=======================================
vPoller - Distributed vSphere API Proxy
=======================================

vPoller is a distributed VMware vSphere API Proxy, designed
for discovering and polling of vSphere objects.

It uses the `VMware vSphere API`_ in order to perform discovery
and polling of vSphere objects.

vPoller uses the `ZeroMQ messaging library`_ for distributing tasks
to workers and load balancing of client requests.

vPoller can be integrated with other systems, which require access to
vSphere objects, but do not have native support for it.

Possible scenarios where vPoller could be used is integration with
monitoring systems as part of the discovery and polling process
in order to provide monitoring of your VMware vSphere environment.

vPoller has been tested with VMware vSphere 5.x and with very
limited testing on vSphere 4.x

vPoller is Open Source and licensed under the `BSD License`_.

.. _`VMware vSphere API`: https://www.vmware.com/support/developer/vc-sdk/
.. _`ZeroMQ messaging library`: http://zeromq.org/
.. _`BSD License`: http://opensource.org/licenses/BSD-2-Clause

Contributions
=============

`vPoller is hosted on Github`_. Please contribute by reporting
issues, suggesting features or by sending patches using pull requests.

.. _`vPoller is hosted on Github`: https://github.com/dnaeon/py-vpoller

Bugs
====

Probably. If you experience a bug issue, please report it to the
`vPoller issue tracker on Github`_

.. _`vPoller issue tracker on Github`: https://github.com/dnaeon/py-vpoller/issues

Getting started
===============

A good place to start with vPoller is to go over the
:ref:`terminology` page in order to get familiar with the concepts and
terms used in vPoller.

Once ready with that go ahead to the :ref:`installation` and
:ref:`configuration` documentations, which provide all the details
about how to install and configure vPoller.

Make sure to also check the :ref:`examples` page and see how to run
your first vPoller task requests.

Contents
========

.. toctree::
   :maxdepth: 2

   installation

.. toctree::
   :maxdepth: 2

   configuration

.. toctree::
   :maxdepth: 2

   services

.. toctree::
   :maxdepth: 2

   helpers

.. toctree::
   :maxdepth: 2

   examples

.. toctree::
   :maxdepth: 2

   api

.. toctree::
   :maxdepth: 2

   vpoller-zabbix

.. toctree::
   :maxdepth: 1

   methods

.. toctree::
   :maxdepth: 1

   terminology
