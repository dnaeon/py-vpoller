.. _installation:

=======================
Installation of vPoller
=======================

This document walks you through the installation of vPoller.

There are a number of ways to install vPoller on your system -
you could either install vPoller from source from the Github repo,
or install via ``pip``.

Requirements
============

On the list below you can see the dependencies of vPoller:

* `Python 2.7.x, 3.2.x or later`_
* `pyVmomi`_
* `vconnector`_
* `pyzmq`_
* `docopt`_

The `C client of vPoller`_ also requires the following packages to be
installed in order to build it:

* Python development files (on Debian systems this is usually
  provided by the ``python-dev`` package)
* `ZeroMQ 4.x Library`_

.. _`Python 2.7.x, 3.2.x or later`: http://python.org/
.. _`pyVmomi`: https://github.com/vmware/pyvmomi
.. _`vconnector`: https://github.com/dnaeon/py-vconnector
.. _`pyzmq`: https://github.com/zeromq/pyzmq
.. _`docopt`: https://github.com/docopt/docopt
.. _`C client of vPoller`: https://github.com/dnaeon/py-vpoller/tree/master/extra/vpoller-cclient
.. _`ZeroMQ 4.x library`: https://github.com/zeromq/zeromq4-x

Installation with pip
=====================

In order to install vPoller using ``pip``, simply execute this command:

.. code-block:: bash

   $ pip install vpoller

If you would like to install vPoller in a ``virtualenv``, then
follow these steps instead:

.. code-block:: bash

   $ virtualenv vpoller-venv
   $ source vpoller-venv/bin/activate
   $ pip install vpoller

Installation from source
========================

The ``master`` branch of vPoller is where main development happens.

In order to install the latest version of vPoller follow these
simple steps:

.. code-block:: bash

    $ git clone https://github.com/dnaeon/py-vpoller.git
    $ cd py-vpoller
    $ sudo python setup.py install

If you would like to install vPoller in a ``virtualenv`` follow
these steps instead:

.. code-block:: bash
		
   $ virtualenv vpoller-venv
   $ source vpoller-venv/bin/activate
   $ git clone https://github.com/dnaeon/py-vpoller.git
   $ cd py-vpoller
   $ python setup.py install

This should take care of installing all dependencies for you
as well.

In order to install one of the stable releases of vPoller please
refer to the page of `vPoller stable releases`_.

.. _`vPoller stable releases`: https://github.com/dnaeon/py-vpoller/releases

Installing the C client of vPoller
==================================

vPoller comes with two client applications - a Python and a C client.

In order to use the C client of vPoller you need to make sure that
you have the `ZeroMQ 4.x library`_ installed as the C client is
linked against it.

Here is how to install the `ZeroMQ 4.x library`_ on your system
from source:

.. code-block:: bash
		
    $ git clone https://github.com/zeromq/zeromq4-x.git
    $ cd zeromq4-x
    $ ./autogen.sh
    $ ./configure
    $ make && sudo make install && make clean
    $ sudo ldconfig

After that building the vPoller C client is as easy as this:

.. code-block:: bash

   $ cd py-vpoller/extra/vpoller-cclient
   $ make

You should now have the ``vpoller-cclient`` executable in your
current directory built and ready for use.
