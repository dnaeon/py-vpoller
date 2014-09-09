.. _helpers:

===============
vPoller Helpers
===============

The ``vPoller Helpers`` were implemented in order to provide an
easy way for connecting your applications to vPoller.

A result messages returned by the ``vpoller-worker`` is always in
JSON format.  This could be okay for most applications, which require
to process a result message, but in some cases you might want to
receive the result in different formats and feed the data into
your application. 

Using the ``vPoller Helpers`` you are able to convert the result
message to a format that your application or system understands.

The table below summarizes the currently existing and
supported ``vPoller Helpers`` along with a short description:

+---------------------------+--------------------------------------------------------+
| vPoller Helper            | Description                                            |
+===========================+========================================================+
| vpoller.helpers.zabbix    | Helper which returns result in Zabbix-friendly format  |
+---------------------------+--------------------------------------------------------+
| vpoller.helpers.csvhelper | Helper which returns result in CSV format              |
+---------------------------+--------------------------------------------------------+

The ``vPoller Helpers`` are simply Python modules and are
loaded by the ``vPoller Workers`` upon startup.

Enabling helpers
================

In order to enable helpers in your ``vPoller Workers`` you need to
specify in the ``vpoller.conf`` file the helper modules, which you
wish to be loaded and available to clients.

Here is a sample ``vpoller.conf`` file which includes the ``helpers``
configuration option for loading the ``zabbix`` helper
module in your ``vPoller Worker``:

.. code-block:: ini

   [proxy]
   frontend = tcp://*:10123
   backend  = tcp://*:10124
   mgmt     = tcp://*:9999
   
   [worker]
   db       = /var/lib/vconnector/vconnector.db
   proxy    = tcp://localhost:10124
   mgmt     = tcp://*:10000
   helpers  = vpoller.helpers.zabbix

vPoller Zabbix Helper
=====================

One of the ``vPoller Helpers`` is the `Zabbix vPoller Helper module`_,
which can translate a result message to `Zabbix LLD format`_ and
return values ready to be used in Zabbix items as well.

.. _`Zabbix vPoller Helper module`: https://github.com/dnaeon/py-vpoller/tree/master/src/vpoller/helpers/zabbix.py
.. _`Zabbix LLD format`: https://www.zabbix.com/documentation/2.2/manual/discovery/low_level_discovery

Here is an example of using the ``Zabbix vPoller Helper``,
which will convert a result message to Zabbix-friendly format:

.. code-block:: bash
		
   $ vpoller-client --method datastore.discover --vsphere-host vc01.example.org \
		--helper vpoller.helpers.zabbix

The ``*.discover`` methods of vPoller when used with the Zabbix helper,
would return data ready in Zabbix LLD format.

When using the ``*.get`` methods of vPoller with the Zabbix helper,
the result would be a single property value, making it suitable
for use in Zabbix items.

This is how to retrieve a property of a ``Datastore`` object using the
Zabbix helper:

.. code-block:: bash

   $ vpoller-client --method vm.get --vsphere-host vc01.example.org \
		--name vm01.example.org --properties runtime.powerState \
		--helper vpoller.helpers.zabbix
	
vPoller CSV Helper
==================

Another vPoller helper is the ``vPoller CSV helper`` which translates
a result message in CSV format.

Here is an example how to get all your Virtual Machines and their
``runtime.powerState`` property in CSV format:

.. code-block:: bash

   $ vpoller-client --method vm.discover --vsphere-host vc01.example.org \
		--properties runtime.powerState \
		--helper vpoller.helpers.csvhelper

And here is a sample result from the above command:

.. code-block:: csv
   
   name,runtime.powerState
   vpoller-vm-1,poweredOn
   vpoller-vm-2,poweredOn
   freebsd-vm-1,poweredOn
   zabbix-vm-1.04-dev,poweredOn

Here is one post that you can read which makes use of the
``vPoller CSV Helper`` in order to export data from a vSphere
environment and plot some nice graphs from it.

* `Exporting Data From a VMware vSphere Environment For Fun And Profit`_

.. _`Exporting Data From a VMware vSphere Environment For Fun And Profit`: http://unix-heaven.org/node/116
   
