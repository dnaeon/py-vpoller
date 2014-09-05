.. _services:

================
vPoller Services
================

vPoller consists of a number of components, each responsible for a
specific task.

This page describes how to manage the ``vpoller-proxy`` and
``vpoller-worker`` services.

Please refer to the :ref:`terminology` page for more
information about the vPoller components and their purpose.

In a production environment you would want to have these services
running as daemons and started at boot-time. At the end of this
documentation we will see how to use a process control system
such as `Supervisord`_ for managing the ``vpoller-proxy`` and
``vpoller-worker`` services.

.. _`Supervisord`: http://supervisord.org/

Starting and stopping the vPoller Proxy
=======================================

In order to start the ``vpoller-proxy`` service simply execute the
command below:

.. code-block:: bash

   $ vpoller-proxy start

After you start the ``vpoller-proxy`` service you should see something
similar, which indicates that the ``vpoller-proxy`` has started
successfully and is ready to distribute tasks to the
``vPoller Workers``.

.. code-block:: bash

   $ vpoller-proxy start
   [2014-09-05 13:26:04,807 - INFO/MainProcess] Starting Proxy Manager
   [2014-09-05 13:26:04,808 - INFO/MainProcess] Creating Proxy Manager sockets
   [2014-09-05 13:26:04,808 - INFO/MainProcess] Starting Proxy process
   [2014-09-05 13:26:04,809 - INFO/MainProcess] Proxy Manager is ready and running
   [2014-09-05 13:26:04,810 - INFO/VPollerProxy-1] Proxy process is starting
   [2014-09-05 13:26:04,810 - INFO/VPollerProxy-1] Creating Proxy process sockets
   [2014-09-05 13:26:04,810 - INFO/VPollerProxy-1] Proxy process is ready and running

In order to stop the ``vpoller-proxy`` service simply hit ``Ctrl+C``,
which would gracefully shutdown the service.

Another way to stop the ``vpoller-proxy`` service is to use the
management interface and send a shutdown signal to the service.

Here is how to shutdown a ``vpoller-proxy`` using the management
interface:

.. code-block:: bash

   $ vpoller-proxy --endpoint tcp://localhost:9999 stop

Starting and stopping the vPoller Worker
========================================

In order to start the ``vpoller-worker`` service simply execute the
command below:

.. code-block:: bash

   $ vpoller-worker start

After you start the ``vpoller-worker`` service you should see
something similar, which indicates that the ``vpoller-worker`` has
started successfully and is ready to process task requests.

.. code-block:: bash

   [2014-09-05 04:26:38,136 - INFO/MainProcess] Starting Worker Manager
   [2014-09-05 04:26:38,138 - INFO/MainProcess] Starting Worker processes
   [2014-09-05 04:26:38,138 - INFO/MainProcess] Concurrency: 1 (processes)
   [2014-09-05 04:26:38,139 - INFO/MainProcess] Worker Manager is ready and running
   [2014-09-05 04:26:38,141 - INFO/VPollerWorker-1] Worker process is starting
   [2014-09-05 04:26:38,142 - INFO/VPollerWorker-1] Creating Worker sockets
   [2014-09-05 04:26:38,144 - INFO/VPollerWorker-1] Worker process is ready and running

By default when you start the ``vpoller-worker`` service it will
create ``worker processes`` equal to the number of cores available
on the target system.

In order to control the concurrency level and how many worker
processes will be started use the ``--concurrency`` option of
``vpoller-worker``.

Here is an example command, which will start ``vpoller-worker``
with 4 worker processes.

.. code-block:: bash
		
   $ vpoller-worker --concurrency 4 start
   [2014-09-05 04:29:56,680 - INFO/MainProcess] Starting Worker Manager
   [2014-09-05 04:29:56,682 - INFO/MainProcess] Starting Worker processes
   [2014-09-05 04:29:56,682 - INFO/MainProcess] Concurrency: 4 (processes)
   [2014-09-05 04:29:56,689 - INFO/VPollerWorker-1] Worker process is starting
   [2014-09-05 04:29:56,694 - INFO/VPollerWorker-1] Creating Worker sockets
   [2014-09-05 04:29:56,691 - INFO/VPollerWorker-2] Worker process is starting
   [2014-09-05 04:29:56,698 - INFO/VPollerWorker-2] Creating Worker sockets
   [2014-09-05 04:29:56,693 - INFO/VPollerWorker-3] Worker process is starting
   [2014-09-05 04:29:56,700 - INFO/VPollerWorker-3] Creating Worker sockets
   [2014-09-05 04:29:56,703 - INFO/VPollerWorker-3] Worker process is ready and running
   [2014-09-05 04:29:56,698 - INFO/VPollerWorker-4] Worker process is starting
   [2014-09-05 04:29:56,703 - INFO/MainProcess] Worker Manager is ready and running
   [2014-09-05 04:29:56,704 - INFO/VPollerWorker-1] Worker process is ready and running
   [2014-09-05 04:29:56,706 - INFO/VPollerWorker-4] Creating Worker sockets
   [2014-09-05 04:29:56,705 - INFO/VPollerWorker-2] Worker process is ready and running
   [2014-09-05 04:29:56,710 - INFO/VPollerWorker-4] Worker process is ready and running

In order to stop the ``vpoller-worker`` service simply hit ``Ctrl+C``,
which would gracefully shutdown the service.

Another way to stop the ``vpoller-worker`` service is to use the
management interface and send a shutdown signal to the service.

Here is how to shutdown a ``vpoller-worker`` using the management
interface:

.. code-block:: bash

   $ vpoller-worker --endpoint tcp://localhost:10000 stop

Using the vPoller Management Interfaces
=======================================

When you start ``vpoller-proxy`` and ``vpoller-worker`` a management
endpoint is available for sending management tasks to the services.

At any time you can request status information from your
vPoller services by sending a request to the management interface.

This is how you could get status information from your
``vpoller-proxy``:

.. code-block:: bash

   $ vpoller-proxy --endpoint tcp://localhost:9999 status

And this is how you could get status information from your
``vpoller-worker``:

.. code-block:: bash
		
   $ vpoller-worker --endpoint tcp://localhost:10000 status

Managing vPoller Services with Supervisord
==========================================

When running vPoller in a production environment you would want to
have the ``vpoller-proxy`` and ``vpoller-worker`` services running as
daemons and started at boot-time.

In this section we will see how to use `Supervisord`_ for managing the
vPoller services.

First, make sure that you have `Supervisord`_ installed on your
system.

After that create the following config file and place it into your
``Supervisord include`` directory.

.. code-block:: ini

   [program:vpoller-proxy]
   command=/usr/bin/vpoller-proxy start
   redirect_stderr=true
   stdout_logfile=/var/log/vpoller/vpoller-proxy.log
   autostart=true
   ;user=myusername
   stopsignal=INT

   [program:vpoller-worker]
   command=/usr/bin/vpoller-worker start
   redirect_stderr=true
   stdout_logfile=/var/log/vpoller/vpoller-worker.log
   autostart=true
   ;user=myusername
   stopsignal=INT

Now reload ``Supervisord`` by executing these commands:

.. code-block:: bash

   $ sudo supervisordtl reread
   $ sudo supervisorctl reload

In order to start the ``vpoller-proxy`` and ``vpoller-worker``
services you would use the ``supervisorctl`` tool.

This is how to start the vPoller services:

.. code-block:: bash

   $ sudo supervisorctl start vpoller-proxy
   $ sudo supervisorctl start vpoller-worker

And this is how to stop the vPoller services:

.. code-block:: bash

   $ sudo supervisorctl stop vpoller-proxy
   $ sudo supervisorctl stop vpoller-worker

For more information about what you can do with ``Supervisord``,
please refer to the official documentation of `Supervisord`_.
