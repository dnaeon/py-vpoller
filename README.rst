vPoller - Distributed VMware vSphere API Proxy
==============================================

.. image:: https://pypip.in/version/vpoller/badge.svg
    :target: https://pypi.python.org/pypi/vpoller/
    :alt: Latest Version

.. image:: https://pypip.in/download/vpoller/badge.svg
    :target: https://pypi.python.org/pypi/vpoller/
    :alt: Downloads

vPoller is a distributed VMware vSphere API Proxy, designed for
discovering and polling of vSphere objects.

It uses the `VMware vSphere API <https://www.vmware.com/support/developer/vc-sdk/>`_
in order to perform discovery and polling of vSphere objects.

vPoller uses the `ZeroMQ messaging library <http://zeromq.org/>`_ for
distributing tasks to workers and load balancing of client requests.

vPoller can be integrated with other systems, which require access to
vSphere objects, but do not have native support for it.

Possible scenarios where vPoller could be used is integration with
monitoring systems as part of the discovery and polling process
in order to provide monitoring of your VMware vSphere environment.

vPoller has been tested with VMware vSphere 5.x and with very limited
testing on vSphere 4.x.

vPoller is Open Source and licensed under the
`BSD License <http://opensource.org/licenses/BSD-2-Clause>`_.

Contributions
=============

vPoller is hosted on `Github <https://github.com/dnaeon/py-vpoller>`_.
Please contribute by reporting issues, suggesting features or by
sending patches using pull requests.

Documentation
=============

The online documentation of vPoller can be found on the link below:

* http://vpoller.readthedocs.org/en/latest/

Bugs
====

Probably. If you experience a bug issue, please report it to the
`vPoller issue tracker on Github <https://github.com/dnaeon/py-vpoller/issues>`_.
