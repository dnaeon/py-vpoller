.. _vpoller-zabbix:

===============================
vPoller Integration With Zabbix
===============================

One of the nice things about vPoller is that it can be easily
integrated with other systems.

In this documentation we will see how we can integrate vPoller with
`Zabbix`_ in order to start monitoring our VMware vSphere environment.

.. _`Zabbix`: http://www.zabbix.com/

**NOTE**: This document is about VMware monitoring with vPoller and
Zabbix, and **NOT** about VMware monitoring with stock Zabbix.

If you are looking for VMware monitoring with stock Zabbix,
please refer to the `official Zabbix documentation`_.

.. _`official Zabbix documentation`: https://www.zabbix.com/documentation/2.2/manual/vm_monitoring

Why use vPoller with Zabbix and not just use stock Zabbix for VMware monitoring?
================================================================================

There are many things that can be put here describing the reasons
and motivation why you might prefer having vPoller with Zabbix
integration instead of stock Zabbix, but eventually this would end
up being one long (and probably boring) story to write and tell.

You can read `this post here`_, which outlines some very good reasons
why you might want to have vPoller with Zabbix instead of stock
Zabbix when it comes to VMware vSphere monitoring.

.. _`this post here`: http://unix-heaven.org/node/114

Prerequisites
=============

This documentation assumes that you already have Zabbix installed
and configured.

Next thing you need to make sure is that you have vPoller installed,
configured and already running.

If you haven't installed and configured vPoller yet, please
refer to the :ref:`installation` and :ref:`configuration`
documentations first.

Importing the vPoller templates in Zabbix
=========================================

You can grab the latest `vPoller templates for Zabbix`_ from the Github
repo of vPoller.

.. _`vPoller templates for Zabbix`: https://github.com/dnaeon/py-vpoller/tree/master/src/zabbix/templates

Once you import the templates you should see the newly imported
vPoller templates.

.. image:: images/vpoller-zabbix-templates.jpg

Native vPoller support for Zabbix
=================================

Native vPoller support for Zabbix will make it possible for
Zabbix to talk natively to vPoller via a `Zabbix loadable module`_

.. _`Zabbix loadable module`: https://www.zabbix.com/documentation/2.2/manual/config/items/loadablemodules

Native vPoller support for Zabbix will be available only for Zabbix
release versions 2.2.x or above, as loadable modules in Zabbix
were introduced since the 2.2.x release of Zabbix.

Native vPoller support for Zabbix is planned for the next release of
vPoller and you can track it's progress in this issue here:

* https://github.com/dnaeon/py-vpoller/issues/51

Setting up vPoller externalscripts for Zabbix
=============================================

**NOTE**: This section of the documentation provides instructions
how to install the vPoller ``externalscripts`` in Zabbix. It is
recommended that you always use the
``native vPoller support for Zabbix`` when integrating vPoller with
Zabbix, and use ``externalscripts`` only if you cannot have the
native vPoller support for Zabbix, e.g. you are running an older
Zabbix release which doesn't support loadable modules or the loadable
module is not available for your platform.

Get the ``vpoller-zabbix`` and ``cvpoller-zabbix`` wrapper scripts
from the links below and place them in your Zabbix
``externalscripts`` directory:

* https://github.com/dnaeon/py-vpoller/blob/master/src/zabbix/externalscripts/vpoller-zabbix
* https://github.com/dnaeon/py-vpoller/blob/master/src/zabbix/externalscripts/cvpoller-zabbix

You can also find user-contributed ``vpoller-zabbix`` and
``cvpoller-zabbix`` wrapper scripts, which come with more features
and safety checks at the links below:

* https://github.com/dnaeon/py-vpoller/blob/master/contrib/zabbix/externalscripts/vpoller-zabbix
* https://github.com/dnaeon/py-vpoller/blob/master/contrib/zabbix/externalscripts/cvpoller-zabbix

Using any of these wrapper scripts should be fine.

Place the ``vpoller-zabbix`` and ``cvpoller-zabbix`` wrapper scripts
into your Zabbix ``externalscripts`` directory and make sure they
are executable as well:

.. code-block:: bash

   $ sudo chmod 0755 $externalscripts/vpoller-zabbix $externalscripts/cvpoller-zabbix

Monitoring your VMware environment with vPoller and Zabbix
==========================================================

Time to start monitoring our VMware vSphere environment with vPoller
and Zabbix. Let's go ahead and add a VMware vCenter server and
get some data out of it.

Login to your Zabbix frontend and navigate to
``Configuration -> Hosts``, then at the top-right corner click on the
``Create host`` button. Fill in the hostname of the vCenter we are
going to monitor and add it to a group, e.g. vCenters in my case.

.. image:: images/vpoller-zabbix-add-host-1.jpg

Next, click on the ``Templates`` and link the
``Template VMware vSphere - vPoller`` template to your vCenter.

.. image:: images/vpoller-zabbix-add-host-2.jpg

The last thing we need to do is add a Zabbix macro to our
vSphere host. Navigate to the ``Macros`` tab and add the
``{$VSPHERE.HOST}`` macro which value should be the hostname of the
vSphere host you are adding to Zabbix.

.. image:: images/vpoller-zabbix-add-host-3.jpg

Once done, click the ``Save`` button and you are ready.

Soon enough Zabbix will start sending requests to vPoller which would
discover your vSphere objects (ESXi hosts, Virtual Machines,
Datastores, etc) and start monitoring them.

Importing vSphere objects as regular Zabbix hosts
=================================================

In the previous section of this documentation we have seen how we
can use Zabbix with vPoller working together in order to perform
monitoring of our VMware vSphere environment.

The way we did it is by using vPoller in order to discover VMware
vSphere objects and then use the `Zabbix Low-level discovery`_
protocol in order to create hosts based on the discovered data.

.. _`Zabbix Low-level discovery`: https://www.zabbix.com/documentation/2.2/manual/discovery/low_level_discovery

While ``Zabbix Low-level discovery`` is a powerful feature of Zabbix
which you could use in order to automate the process of discovering
and adding hosts to your Zabbix server, it still has some limitations
and disadvantages.

One disadvantage of using Zabbix LLD is that once a host is being
created by a Zabbix Discovery Rule that host becomes immutable -
you cannot manually change or update anything on the host,
unless these changes come from the discovery rule or the host profile
applied to the host.

You can imagine that this might be a bit of frustrating when you want
to group your hosts in a better way for example, which obviously you
cannot do since this host is now immutable.

Linking additional templates to a discovered host is also not
possible, which is another big issue. Now that you've discovered your
VMware Virtual Machines you probably wanted to link some additional
templates to them, but you will soon discover that this is not
possible either.

You cannot even add more interfaces to your hosts if needed...
Like mentioned earlier - your host is immutable, so that means
no changes at all after your hosts have been discovered with a
Zabbix LLD rule.

And all these things are quite frustrating, at least to me, because
Zabbix does not allow me to manage my environment the way I want.

So, what can we do about it?

Well, we can solve this issue! And vPoller is going to help us do that! :)

We are going to use the `zabbix-vsphere-import`_ tool, which can
discover and import vSphere objects as regular Zabbix hosts -
that means that all vSphere objects (ESXi hosts, Virtual Machines,
Datastores, etc.) which were imported by the `zabbix-vsphere-import`_
tool would be regular Zabbix hosts, which you could update -
adding the host to groups you want, linking arbitrary
templates to it, etc.

.. _`zabbix-vsphere-import`: https://github.com/dnaeon/py-vpoller/tree/master/src/zabbix/vsphere-import

First, let's create the config file which `zabbix-vsphere-import`_
will be using. Below is an example config file used by
``zabbix-vsphere-import`` tool:

.. code-block:: yaml

   ---
   vsphere:
     hostname: vc01.example.org
   
   vpoller:
     endpoint: tcp://localhost:10123
     retries: 3
     timeout: 3000

   zabbix:
     hostname: http://zabbix.example.org/zabbix
     username: Admin
     password: zabbix

   vsphere_object_host:
     proxy: zbx-proxy.example.org
     templates:
       - Template VMware vSphere Hypervisor - vPoller
     macros:
       VSPHERE.HOST: vc01.example.org
     groups:
       - Hypervisors

   vsphere_object_vm:
     templates:
       - Template VMware vSphere Virtual Machine - vPoller
     macros:
       VSPHERE.HOST: vc01.example.org
     groups:
       - Virtual Machines

   vsphere_object_datastore:
     templates:
       - Template VMware vSphere Datastore - vPoller
     macros:
       VSPHERE.HOST: vc01.example.org
     groups:
       - Datastores

In the example config file above we have defined various config
entries - Zabbix server, Zabbix Proxy which will be used,
vPoller settings and also templates to be linked for the various
vSphere objects.

As you can see the format of the configuration file allows for
flexible setup of your discovered vSphere objects.

Time to import our vSphere objects as regular Zabbix hosts.
To do that simply execute the command below:

.. code-block:: bash

   $ zabbix-vsphere-import -f zabbix-vsphere-import.yaml

Here is an example output of running the `zabbix-vsphere-import`_
tool:

.. code-block:: bash

   $ zabbix-vsphere-import -f zabbix-vsphere-import.yaml 
   [2014-09-06 10:33:28,420] - INFO - Connecting to Zabbix server at http://zabbix.example.org/zabbix
   [2014-09-06 10:33:28,537] - INFO - [vSphere ClusterComputeResource] Importing objects to Zabbix
   [2014-09-06 10:33:28,814] - INFO - [vSphere ClusterComputeResource] Number of objects to be imported: 1
   [2014-09-06 10:33:28,814] - INFO - [vSphere ClusterComputeResource] Creating Zabbix host group 'cluster01'
   [2014-09-06 10:33:28,904] - INFO - [vSphere ClusterComputeResource] Import of objects completed
   [2014-09-06 10:33:28,904] - INFO - [vSphere HostSystem] Importing objects to Zabbix
   [2014-09-06 10:33:29,122] - INFO - [vSphere HostSystem] Number of objects to be imported: 2
   [2014-09-06 10:33:29,289] - INFO - [vSphere HostSystem] Creating Zabbix host 'esxi01.example.org'
   [2014-09-06 10:33:30,204] - INFO - [vSphere HostSystem] Creating Zabbix host 'esxi02.example.org'
   [2014-09-06 10:33:30,658] - INFO - [vSphere HostSystem] Import of objects completed
   [2014-09-06 10:33:30,658] - INFO - [vSphere VirtualMachine] Importing objects to Zabbix
   [2014-09-06 10:33:30,775] - INFO - [vSphere VirtualMachine] Number of objects to be imported: 9
   [2014-09-06 10:33:30,935] - WARNING - Unable to find Zabbix host group 'Virtual Machines'
   [2014-09-06 10:33:30,936] - INFO - Creating Zabbix host group 'Virtual Machines'
   [2014-09-06 10:33:33,965] - INFO - [vSphere VirtualMachine] Creating Zabbix host 'ubuntu-14.04-dev'
   [2014-09-06 10:33:34,956] - INFO - [vSphere VirtualMachine] Creating Zabbix host 'centos-6.5-amd64'
   [2014-09-06 10:33:35,945] - INFO - [vSphere VirtualMachine] Creating Zabbix host 'sof-vc0-mnik'
   [2014-09-06 10:33:36,441] - INFO - [vSphere VirtualMachine] Creating Zabbix host 'test-vm-01'
   [2014-09-06 10:33:36,934] - INFO - [vSphere VirtualMachine] Creating Zabbix host 'sof-dev-d7-mnik'
   [2014-09-06 10:33:37,432] - INFO - [vSphere VirtualMachine] Creating Zabbix host 'ubuntu-12.04-desktop'
   [2014-09-06 10:33:43,430] - INFO - [vSphere VirtualMachine] Creating Zabbix host 'zabbix-vm-2'
   [2014-09-06 10:33:43,929] - INFO - [vSphere VirtualMachine] Creating Zabbix host 'zabbix-vm-1'
   [2014-09-06 10:33:44,432] - INFO - [vSphere VirtualMachine] Creating Zabbix host 'VMware vCenter Server Appliance'
   [2014-09-06 10:33:44,937] - INFO - [vSphere VirtualMachine] Import of objects completed
   [2014-09-06 10:33:44,937] - INFO - [vSphere Datastore] Importing objects to Zabbix
   [2014-09-06 10:33:45,046] - INFO - [vSphere Datastore] Number of objects to be imported: 1
   [2014-09-06 10:33:45,339] - INFO - [vSphere Datastore] Creating host 'ds:///vmfs/volumes/5190e2a7-d2b7c58e-b1e2-90b11c29079d/'
   [2014-09-06 10:33:45,607] - INFO - [vSphere Datastore] Import of objects completed

Generally you would want to run the import perhaps once an hour
(e.g. from ``cron(8)``), so that your Zabbix server is in sync with
your vSphere environment.

Example screenshots
===================

Let's see some example screenshots of Zabbix monitoring a
VMware vSphere environment using vPoller.

Checking the latest data of our vCenter server in Zabbix:

.. image:: images/vpoller-zabbix-data-1.jpg

Let's see the latest data for some of our ESXi hosts:

.. image:: images/vpoller-zabbix-data-2.jpg

Another screenshot showing information about our ESXi host:

.. image:: images/vpoller-zabbix-data-3.jpg

And another screenshot showing hardware related information about
our ESXi host:

.. image:: images/vpoller-zabbix-data-4.jpg

Let's check the latest data for one of our Virtual Machines:

.. image:: images/vpoller-zabbix-data-5.jpg

A screenshot showing information about the file systems in
Virtual Machine:

.. image:: images/vpoller-zabbix-data-6.jpg

Another screenshot showing general information about a Virtual
Machine:

.. image:: images/vpoller-zabbix-data-7.jpg

And one more screenshot showing information about the memory and
VMware Tools for our Virtual Machine:

.. image:: images/vpoller-zabbix-data-8.jpg

