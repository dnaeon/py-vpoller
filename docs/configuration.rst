.. _configuration:

========================
Configuration of vPoller
========================

The default configuration file of vPoller resides in a single
file and it's default location is ``/etc/vpoller/vpoller.conf``.

Below is an example ``vpoller.conf`` file that you can use:

.. code-block:: ini

   [proxy]
   frontend = tcp://*:10123
   backend  = tcp://*:10124
   mgmt     = tcp://*:9999
   
   [worker]
   db       = /var/lib/vconnector/vconnector.db
   proxy    = tcp://localhost:10124
   mgmt     = tcp://*:10000

The table below provides information about the config entries
used along with a description for each of them.

+---------+-----------+-----------------------------------------------------------------------------------+
| Section | Option    | Description                                                                       |
+=========+===========+===================================================================================+
| proxy   | frontend  | Endpoint to which clients connect and send tasks for processing                   |
+---------+-----------+-----------------------------------------------------------------------------------+
| proxy   | backend   | Endpoint to which workers connect and get tasks for processing                    |
+---------+-----------+-----------------------------------------------------------------------------------+
| proxy   | mgmt      | Management endpoint, used for management tasks of the ``vPoller Proxy``           |
+---------+-----------+-----------------------------------------------------------------------------------+
| worker  | db        | Path to the ``vconnector.db`` SQLite database file                                |
+---------+-----------+-----------------------------------------------------------------------------------+
| worker  | proxy     | Endpoint to which workers connect and get tasks for processing                    |
+---------+-----------+-----------------------------------------------------------------------------------+
| worker  | mgmt      | Management endpoint, used for management tasks for the ``vPoller Worker``         |
+---------+-----------+-----------------------------------------------------------------------------------+

Configuring vSphere Agents for the Workers
==========================================

The ``vSphere Agents`` are the ones that take care of establishing
connections to the vSphere hosts and perform discovery and polling
of vSphere objects.

A ``vPoller Worker`` can have as many ``vSphere Agents`` as you want,
which means that a single ``vPoller Worker`` can be used to monitor
multiple vSphere hosts (ESXi hosts, vCenter servers).

Connection details (username, password, host) about each
``vSphere Agent`` are stored in a `SQLite`_ database and are
managed by the `vconnector-cli`_ tool.

.. _`vconnector-cli`: https://github.com/dnaeon/py-vconnector
.. _`SQLite`: http://www.sqlite.org/

.. note::

   The example commands below use the ``root`` account for
   configuring a vSphere Agent for a vCenter Server.

   The ``root`` account in a vCenter Server by default has full
   administrative privileges.

   If security is a concern you should use an account for your
   vSphere Agents that has a restricted set of privileges.

First let's initialize the ``vConnector`` database file:

.. code-block:: bash
   
   $ sudo vconnector-cli init

By default the ``vconnector.db`` database file resides in
``/var/lib/vconnector/vconnector.db``, unless you specify an
alternate location from the command-line.

Now, let's add one ``vSphere Agent``, which can later be used by
our ``vPoller Worker``.

This is how to add a new ``vSphere Agent`` using ``vconnector-cli``:

.. code-block:: bash
		
   $ sudo vconnector-cli -H vc01.example.org -U root -P p4ssw0rd add

When you create a new ``vSphere Agent`` by default it will be
disabled, so in order to use that agent in your ``vPoller Worker``
you should enable it first.

This is how to enable a ``vSphere Agent``:

.. code-block:: bash

   $ sudo vconnector-cli -H vc01.example.org enable

At any time you can view the currently registered ``vSphere Agents``
by running the ``vconnector-cli get`` command, e.g.:

.. code-block:: bash

   $ sudo vconnector-cli get
   +------------------+------------+------------+-----------+
   | Hostname         | Username   | Password   |   Enabled |
   +==================+============+============+===========+
   | vc01.example.org | root       | p4ssw0rd   |         1 |
   +------------------+------------+------------+-----------+

As the ``vconnector.db`` database contains connection details about
your VMware vSphere hosts in order to avoid any leak of sensitive
data you would want to secure this file and make it readable only
by the user, which runs the ``vPoller Worker``.

