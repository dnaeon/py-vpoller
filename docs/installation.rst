.. _installation:

=======================
Installation of vPoller
=======================

This document walks you through the installation of vPoller.

There are a number of ways to install vPoller on your system -
you could either install vPoller from source from the Github repo or
use binary packages.

As of now binary packages of vPoller are only available for
`Debian GNU/Linux`_ systems.

.. _`Debian GNU/Linux`: http://debian.org/

Requirements
============

On the list below you can see the dependencies of vPoller:

* `Python 2.7.x`_
* `pyVmomi`_
* `vconnector`_
* `pyzmq`_
* `docopt`_

The `C client of vPoller`_ also requires the following packages to be
installed in order to build it:

* Python development files (on Debian systems this is usually
  provided by the ``python-dev`` package)
* `ZeroMQ 4.x Library`_

.. _`Python 2.7.x`: http://python.org/
.. _`pyVmomi`: https://github.com/vmware/pyvmomi
.. _`vconnector`: https://github.com/dnaeon/py-vconnector
.. _`pyzmq`: https://github.com/zeromq/pyzmq
.. _`docopt`: https://github.com/docopt/docopt
.. _`C client of vPoller`: https://github.com/dnaeon/py-vpoller/tree/master/src/vpoller-cclient
.. _`ZeroMQ 4.x library`: https://github.com/zeromq/zeromq4-x

Installation with pip
=====================

Coming soon.

Installation from packages
==========================

In order to install vPoller from packages on `Debian GNU/Linux`_
system you can use the Debian packages from the link below:

* `Debian GNU/Linux packages for vPoller`_

.. _`Debian GNU/Linux packages for vPoller`: http://jenkins.unix-heaven.org/job/py-vpoller/

Currently only Debian GNU/Linux packages are available.

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

Here is how to install the `ZeroMQ 4.x library` on your system
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

   $ cd py-vpoller/src/vpoller-cclient
   $ make

You should now have the ``vpoller-cclient`` executable in your
current directory built and ready for use.
