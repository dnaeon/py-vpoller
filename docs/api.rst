.. _api:

=============
Using the API
=============

In this document we will see some examples on how to use the
vPoller API.

You can use these examples for connecting your project to vPoller
and send task requests for processing.

Sending task requests for processing
====================================

Connecting your Python project to vPoller is easy.

If you only need to be able to talk to vPoller and send task requests
then using the ``VPollerClient`` class is the way to go.

The ``VPollerClient`` sends task requests to the ``vPoller Proxy``,
which distributes the task requests to the ``vPoller Workers``.

Here is how you can send task requests from your Python project
to vPoller for processing.

.. code-block:: python

   >>> from vpoller.client import VPollerClient
   >>> msg = {'method': 'vm.discover', 'hostname': 'vc01.example.org'}
   >>> client = VPollerClient(endpoint='tcp://localhost:10123')
   >>> result = client.run(msg)
   >>> print result

The above example code will send a task request for
discovering all Virtual Machine managed objects from the
``vc01.example.org`` vSphere host.

And here is what the above example code does:

1. Imports the ``VPollerClient`` class from the ``vpoller.client``
   module

2. Creates a message that will be sent to the ``vPoller Proxy``
   endpoint. The message contains information such as the
   ``method`` to be processed, the vSphere hostname, and any
   additional details required for processing the task request.

3. We instantiate a ``VPollerClient`` object and set the endpoint
   to which the client will connect and send the task request for
   processing.

4. Using the ``run()`` method of a ``VPollerClient`` instance we
   send the task request over the wire and wait for response.

The ``VPollerClient`` class comes with builtin mechanism for automatic
retry if it doesn't receive a response after some period of time.

In order to control the ``retry`` and ``timeout`` settings of a
``VPollerClient`` object you can instantiate a client object this way:

.. code-block:: python

   >>> client = VPollerClient(                                                                                          
   ...     endpoint='tcp://localhost:10123',                                                                                             
   ...     retries=1,                                                                                                   
   ...     timeout=1000
   ... )

Note, that the ``timeout`` argument used above is in milliseconds.

Here is another example which would get the ``runtime.powerState``
property for a specific Virtual Machine:

.. code-block:: python

   >>> import json
   >>> from vpoller.client import VPollerClient
   >>> msg = {
   ...     'method': 'vm.get',
   ...     'hostname': 'vc01.example.org',
   ...     'name': 'vm01.example.org',
   ...     'properties': ['name', 'runtime.powerState']
   ... }
   >>> client = VPollerClient(endpoint='tcp://localhost:10123')
   >>> result = client.run(msg)
   >>> print json.dumps(result, indent=4)
   {
       "msg": "Successfully retrieved object properties", 
       "result": [
           {
                "runtime.powerState": "poweredOn", 
		"name": "vm01.example.org"
	   }
       ], 
       "success": 0
   }

As you can see we have successfully retrieved the
``runtime.powerState`` property for our Virtual Machine, which shows
that our Virtual Machine is powered on.

For a full list of supported vPoller methods which you can use,
please refer to the :ref:`methods` documentation.

You are also advised to check the `vpoller.agent module`_, which
is pretty well documented and provides information about each
vPoller method and the expected message request in order to begin
processing the task.

.. _`vpoller.agent module`: https://github.com/dnaeon/py-vpoller/blob/master/src/vpoller/agent.py

Executing vPoller tasks locally
===============================

Using the ``VPollerClient`` class as we've seen in the previous
section of this document sends task requests to the
``vPoller Proxy``, which distributes the tasks to any connected
``vPoller Worker``.

This was a remote operation, where a client simply sends a task
request and waits for a response.

You could also use vPoller in order to execute tasks locally,
which means that no task is send over the wire and all the hard
work is done on the local system.

Here is an example of interfacing with the ``vSphere Agents``, which
provides us with an interface to execute vPoller tasks locally.

The example below is equivalent to the examples in the previous
section, except for one thing - it will be executed locally
on the system running this code, and it will not be
processed by a remote worker.

.. code-block:: python

   >>> from vpoller.agent import VSphereAgent
   >>> agent = VSphereAgent(
   ...     user='root',
   ...     pwd='p4ssw0rd',
   ...     host='vc01.example.org'
   ... )
   >>> agent.connect()
   >>> result = agent.vm_discover(msg={})                                                                                   
   >>> print result

Interfacing with vPoller from other languages
=============================================

Connecting to vPoller from other languages is easy as well.

vPoller uses the `ZeroMQ messaging library`_ as the communication
layer, so in theory every language that comes with ZeroMQ bindings
should be able to interface with vPoller.

You can find below a simple example of using `Ruby`_ for sending a
task request to vPoller:

.. _`ZeroMQ messaging library`: http://zeromq.org/
.. _`Ruby`: https://www.ruby-lang.org/en/

.. code-block:: ruby

   #!/usr/bin/env ruby                                                                                                                                                              
   
   require 'json'
   require 'rubygems'
   require 'ffi-rzmq'

   # Message we send to vPoller                                                                                                                                                     
   msg = {:method => "vm.discover", :hostname => "vc01.example.org"}

   # Create the ZeroMQ context and socket                                                                                                                                           
   context = ZMQ::Context.new(1)
   socket = context.socket(ZMQ::REQ)

   puts "Connecting to vPoller ..."
   socket.connect("tcp://localhost:10123")

   puts "Sending task request to vPoller ..."
   socket.send_string(msg.to_json)

   result = ''
   socket.recv_string(result)
   
   puts "Received reply from vPoller: #{result}"

You might also want to check the `vpoller.client module`_ for example
code that you can use in order to implement a ``VPollerClient`` class
in your language of choice.

.. _`vpoller.client module`: https://github.com/dnaeon/py-vpoller/blob/master/src/vpoller/client.py
