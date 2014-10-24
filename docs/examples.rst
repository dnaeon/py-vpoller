.. _examples:

========================
Example usage of vPoller
========================

This page provides some examples how vPoller can be
used to perform various operations like discovery and polling of
VMware vSphere objects.

Please also refer to the :ref:`methods` documentation
for the full list of supported vPoller methods you could use.

The property names which we use in these examples can be found in the
official `VMware vSphere API documentation`_.

Each vSphere managed object has specific properties, which are
documented in the official documentation.

The examples here serve for demonstration purpose only and do not
provide all the properties you could use and get from vSphere objects,
so make sure to refer to the official vSphere documentation when
looking for a specific property name.

There are also a number of posts about how vPoller is being used
for various purposes, which you could also read at the following
links:

* `VMware vSphere CLI tips & tricks with vPoller`_
* `VMware monitoring with Zabbix, Python & vPoller`_
* `Exporting Data From a VMware vSphere Environment For Fun And Profit`_

.. _`VMware vSphere CLI tips & tricks with vPoller`: http://unix-heaven.org/node/111
.. _`VMware monitoring with Zabbix, Python & vPoller`: http://unix-heaven.org/node/114
.. _`Exporting Data From a VMware vSphere Environment For Fun And Profit`: http://unix-heaven.org/node/116
.. _`VMware vSphere API documentation`: https://www.vmware.com/support/developer/vc-sdk/

Datacenter examples
===================

Here is how to discover all ``Datacenter`` objects from your vSphere
environment:

.. code-block:: bash
		
   $ vpoller-client --method datacenter.discover --vsphere-host vc01.example.org

An example command that would get the `summary.overallStatus`
property of a specific ``Datacenter``:

.. code-block:: bash

   $ vpoller-client --method datacenter.get --vsphere-host vc01.example.org \
		--name datacenter01 --properties name,overallStatus

ClusterComputeResource examples
===============================

A ``ClusterComputeResource`` managed object is what you are used to
refer to simply as ``cluster`` in vSphere. The examples commands below
show how to discover and get properties for your vSphere clusters.

An example command to discover all ``ClusterComputeResource``
managed objects from your vSphere environment:

.. code-block:: bash
		
   $ vpoller-client --method cluster.discover --vsphere-host vc01.example.org

And here is how to get the ``overallStatus`` property for a specific
``ClusterComputeResource`` managed object:

.. code-block:: bash

   $ vpoller-client --method cluster.get --vsphere-host vc01.example.org \
		--name cluster01 --properties name,overallStatus

HostSystem examples
===================

``HostSystem`` managed objects in vSphere are your ESXi hosts.

Here is an example how to discover all your ESXi hosts from your
vSphere environment:

.. code-block:: bash
		
   $ vpoller-client --method host.discover --vsphere-host vc01.example.org

And here is an example command to get the ``runtime.powerState``
property for a specific ``HostSystem`` object:

.. code-block:: bash

   $ vpoller-client --method host.get --vsphere-host vc01.example.org \
		--name esxi01.example.org --properties runtime.powerState

An example command to get all Virtual Machines registered on a
specific ESXi host:

.. code-block:: bash
		
   $ vpoller-client --method host.vm.get --vsphere-host vc01.example.org \
		--name esxi01.example.org

VirtualMachine examples
=======================

An example command to discover all ``VirtualMachine`` managed
objects from your vSphere environment:

.. code-block:: bash
		
   $ vpoller-client --method vm.discover --vsphere-host vc01.example.org

Another example showing how to get the ``runtime.powerState``
property of a Virtual Machine:

.. code-block:: bash

   $ vpoller-client --method vm.get --vsphere-host vc01.example.org \
		--name vm01.example.org --properties runtime.powerState

This is how you could discover all disks in a Virtual Machine. Note,
that this method requires that you have VMware Tools installed and
running on the target Virtual Machine:

.. code-block:: bash
   
   $ vpoller-client --method vm.disk.discover --vsphere-host vc01.example.org \
		--name vm01.example.org

If you want to get information about a disk in a Virtual Machine you
could use the ``vm.disk.get`` vPoller method. This is how to get the
``freeSpace`` property for a Virtual Machine disk:

.. code-block:: bash
		
   $ vpoller-client --method vm.disk.get --vsphere-host vc01.example.org \
		--name vm01.example.org --properties freeSpace --key /var

In order to find out the host on which a specific Virtual Machine is
running on you could use the ``vm.host.get`` vPoller method:

.. code-block:: bash
		
   $ vpoller-client --method vm.host.get --vsphere-host vc01.example.org \
		--name vm01.example.org

Using the ``vm.process.get`` vPoller method we can get a list of all
processes running in a Virtual Machine. Note, that we need to supply a
username and password when using the ``vm.process.get`` method, which
are used for authentication in the guest system.

.. code-block:: bash

   $ vpoller-client --method vm.process.get --vsphere-host vc01.example.org \
		--name vm01.example.org --properties name,owner,pid,cmdLine \
		--guest-username root --guest-password p4ssw0rd

.. note::

   The above example command uses the ``root`` user for authentication
   in the guest system. It is recommended that you use a user
   with restricted privileges when using the ``vm.process.get``
   vPoller method if security is a concern.

Datastore examples
==================

Here is an example command which will discover all ``Datastore``
managed objects from your vSphere environment:

.. code-block:: bash

   $ vpoller-client --method datastore.discover --vsphere-host vc01.example.org

This example command below would return the ``summary.capacity``
property for a specific ``Datastore`` object.

.. code-block:: bash
		
   $ vpoller-client --method datastore.get --vsphere-host vc01.example.org \
		-name ds:///vmfs/volumes/5190e2a7-d2b7c58e-b1e2-90b11c29079d/ \
		--properties summary.capacity

This example command will give you all hosts, which are using a
specific ``Datastore``.

.. code-block:: bash

   $ vpoller-client --method datastore.host.get --vsphere-host vc01.example.org \
		--name ds:///vmfs/volumes/5190e2a7-d2b7c58e-b1e2-90b11c29079d/
		
Viewing established Sessions
============================

vPoller can also be used for viewing the established
sessions to your vSphere hosts.

.. note::

   Viewing vSphere sessions by unauthorized parties may be
   considered as a security hole, as it may provide an attacker
   with information such as Session IDs, which could be used for
   spoofing a user's session.

   If security is a concern make sure that your ``vSphere Agents`` are
   configured to use an account with restricted set of privileges,
   which cannot view the established vSphere sessions.

Here is an example command that will return the established sessions
for your vSphere host:

.. code-block:: bash

   $ vpoller-client --method session.get --vsphere-host vc01.example.org

