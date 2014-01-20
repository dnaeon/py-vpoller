## vPoller -- VMware vSphere Distributed Pollers written in Python

*vPoller* is a distributed system written in Python for discoverying and polling of vSphere Objects properties.

*vPoller* uses the [vSphere API](https://www.vmware.com/support/developer/vc-sdk/) in order to perform discovery and polling of *Objects* from a vSphere host (e.g. ESXi or vCenter server instance).

The *vPoller* system consists of a number of components, each performing a different task:

* *vpoller-proxy* - A ZeroMQ proxy which load-balances client requests to a pool of workers
* *vpoller-worker* - A vSphere Worker, which does the actual polling and discovering from a vSphere host
* *vpoller-client* - A client program used for sending and receiving requests to a vSphere Worker

Below you can find more information about the different components along with instructions on how to install and configure them.

The distributed nature of *vPoller* is provided by [ZeroMQ](http://zeromq.org/), which also load balances client requests to a pool of vSphere Workers.

vPoller was designed to be easy for integration into systems which require access to vSphere Objects properties, but do not have native support for it. 

Possible scenarios where *vPoller* could be used is to integrate it into monitoring systems as part of the polling process in order to provide monitoring of your vSphere hosts. It could also be used in applications for collecting statistics and other metrics from your vSphere environment.

vPoller can also be described as a vSphere API-Proxy, because it translates user requests to vSphere API requests thus allowing the user to use the API without having the need to know how the vSphere API works internally.

vPoller has been tested with vSphere 5.x and with very limited testing on vSphere 4.x

You might also want to check this [introduction post about vPoller](http://unix-heaven.org/node/103), which contains real-world usage examples of *vPoller*.

## Requirements

* Python 2.7.x
* [vconnector](https://github.com/dnaeon/py-vconnector)
* [pysphere](https://code.google.com/p/pysphere/)
* [pyzmq](https://github.com/zeromq/pyzmq)
* [docopt](https://github.com/docopt/docopt)

The C client of *vPoller* also requires the following packages to be installed in order to build it:

* Python development files (on Debian systems this is usually provided by the *python-dev* package)
* [ZeroMQ library](https://github.com/zeromq/zeromq3-x)

## Contributions

*vPoller* is hosted on Github. Please contribute by reporting issues, suggesting features or by sending patches using pull requests.

If you like this project please also consider supporting development using [Gittip](https://www.gittip.com/dnaeon/). Thank you!

## Installation

In order to install *vPoller* simply execute the command below:

	# python setup.py install
	
And that's it. Now go ahead to the next section which explains how to configure the vPoller components.

We need to create a few directories as well, which are used by the *vPoller* components to store their log files and lock files as well, so make sure you create them first:

	# mkdir /var/log/vpoller /var/run/vpoller
	
Future versions of *vPoller* will probably provide ready to use packages, so this will be taken care of at that stage as well.
	
## vPoller Proxy

The vPoller Proxy is a ZeroMQ proxy which load-balances client requests between a pool of vSphere workers. 

This is the endpoint where clients connect to in order to have their requests dispatched to the workers.

The default configuration file of the *vpoller-proxy* resides in */etc/vpoller/vpoller-proxy.conf*, although you can specify a different config file from the command-line as well.

Below is an example configuration file used by the *vpoller-proxy*:

	[Default]
	frontend = tcp://*:10123
	backend  = tcp://*:10124
	mgmt     = tcp://*:9999

Here is what the config entries mean:

* **frontend** - The endpoint which clients connect to
* **backend** - The endpoint which vSphere workers connect to
* **mgmt** - An endpoint used for management tasks

Starting the vPoller Proxy is now as easy as just executing the command below:

	# vpoller-proxy start
	
NOTE: You can also find init.d script in the repo for Debian-based systems, which is probably what you would want to run during boot-time.

Run the command below in order to get help and usage information:
	
	# vpoller-proxy --help
	
Checking the log file of *vpoller-proxy* should indicate that it started successfully or contain errors in case something went wrong. 

## vPoller Worker

The vPoller Worker is what does the actual polling and discovering of vSphere objects from a vSphere host.

Internally it runs the vSphere Agents, which take care of connecting to a vSphere host, initiating the user's API requests and send back the result to the client.

A vPoller Worker can connect to any number of vSphere hosts, where each vSphere connection is handled by a separate vSphere Agent object.

The vPoller Worker is connected to a vPoller Proxy through a ZeroMQ socket, from where it receives any requests for processing.

Generally you would be running one vPoller Worker per node in order to provide redundancy of your workers. Automatic load-balancing is provided by the vPoller Proxy.

The table below summarizes the methods `vPoller Worker` currently supports and processes:

| Method               | Description                                        |
|----------------------|----------------------------------------------------|
| host.get             | Get properties of a HostSystem object (ESXi host)  |
| datastore.get        | Get properties of a Datastore object               |
| vm.get               | Get properties of a VirtualMachine object          |
| datacenter.get       | Get properties a Datacenter object                 |
| cluster.get          | Get property of a ClusterComputeResource object    |
| host.discover        | Discovers all HostSystem objects (ESXi hosts)      |
| datastore.discover   | Discovers all Datastores objects                   | 
| vm.discover          | Discovers all VirtualMachine objects               |
| datacenter.discover  | Discovers all Datacenter objects                   |
| cluster.discover     | Discovers all ClusterComputeResources objects      |

The default configuration file of the *vpoller-worker* resides in */etc/vpoller/vpoller-worker.conf*, although you can specify a different config file from the command-line as well.

Below is an example configuration file used by the *vpoller-worker*:

	[Default]
	proxy             = tcp://localhost:10124
	mgmt              = tcp://*:10000
	vsphere_hosts_dir = /etc/vpoller/vsphere
	
Here is an explanation of the config entries above:

* **proxy** - This is the endpoint of the ZeroMQ proxy that the vPoller Worker will connect to in order to receive any client requests
* **mgmt** - This is the vPoller Worker management endpoint
* **vsphere_hosts_dir** - Should be set to a directory which contains *.conf* files for the vSphere Agents. 

As mentioned already a vSphere Agent is what takes care of establishing a connection to the vSphere host and perform any poll or discovery operations. 
For each vSphere host you want to use you need a configuration file describing the connection details.

Below is an example configuration file */etc/vpoller/vsphere/my-vc0.conf*, which describes the connection details to our vCenter server.

	[Default]
	hostname = vc01-test.example.org
	username = root
	password = myp4ssw0rd
	timeout  = 3
	cachettl = 30

You should take care of securing the files as well, as they contain the password in plain text. Now, let's start the vPoller Worker.

	# vpoller-worker start
	
NOTE: You can also find init.d script in the repo for Debian-based systems, which is probably what you would want to run during boot-time.
	
Run the command below in order to get help and usage information:

	# vpoller-worker --help
	
Checking the log file of *vpoller-worker* should indicate that it started successfully or contain errors in case something went wrong. 

## vPoller Client

The vPoller Client is the client application used for sending requests to the vSphere Workers.

Considering that you have your vPoller Proxy and Workers up and running we can now send some example requests to our workers.

The message we send by using vPoller Client is sent to the vPoller Proxy which in turn will perform load-balancing and dispatch the message to our vPoller Workers.

Of course all this is transparent to the user as you only need to send your message to the vPoller Proxy.

In order to get help and usage information about the *vpoller-client*, execute the command below.

	$ vpoller-client --help

The documentation below provides examples how to use the vPoller Client in order to send requests to the vSphere Workers.

## vPoller Helpers

The *vPoller Helpers* were implemented in order to provide an easy way for connecting your applications to *vPoller*.

The result messages returned by a vPoller Worker are always in JSON format. 

This could be okay for most applications, which require to process a result message, but in some cases you might want to
receive the result in different formats and feed the data into your application. 

Using the *vPoller Helpers* you are able to convert the result message to a format that your application or system understands.

An example of such a *vPoller Helper* is the [Zabbix vPoller Helper module](https://github.com/dnaeon/py-vpoller/tree/master/src/vpoller/helpers), which can
translate a result message to [Zabbix LLD format](https://www.zabbix.com/documentation/2.2/manual/discovery/low_level_discovery) and return
property values ready to be used in Zabbix items.

Here is an example of using the *Zabbix vPoller Helper* for converting the results to *Zabbix LLD format*:

	$ vpoller-client -H vpoller.helpers.zabbix -m datastore.discover -e tcp://localhost:10123 -V vc01.example.org
	
This is how you could use the `vpoller.helpers.zabbix` helper to retrieve a property of a vSphere Object.

	$ vpoller-client -H vpoller.helpers.zabbix -m datastore.get -e tcp://localhost:10123 -V vc01.example.org -n <datastore-url> -p summary.capacity
	
This would return just the value of the property requested, thus making it easy for integrating into a *Zabbix Item*.

Possible other usage of the *vPoller Helpers* is an HTML helper, which would return the result in HTML format in order to present the information nicely in a web browser.

The table below summarizes the currently existing and supported `vPoller Helpers`:

| Helper                    | Description                                          |
|---------------------------|------------------------------------------------------|
| vpoller.helpers.zabbix    | Helper which returns data in Zabbix-friendly format  |
| vpoller.helpers.csvhelper | Helper which returns data in CSV format              |

## Discovering ESXi hosts

The method we use for discovering the ESXi hosts is `host.discover`. Below is an example command for discovering all ESXi hosts:

	$ vpoller-client -m host.discover -V vc01-test.example.org -e tcp://localhost:10123

## Discovering Datastores

The method we use for discovering datastores is `datastore.discover`. Below is an example command for discovering all datastores:

	$ vpoller-client -m datastore.discover -V vc01-test.example.org -e tcp://localhost:10123

## Discovering Virtual Machines

The method we use for discovering datastores is `vm.discover`. Below is an example command for discovering all Virtual Machines:

	$ vpoller-client -m vm.discover -V vc01-test.example.org -e tcp://localhost:10123

## Discovering Datacenters

The method we use for discovering datacenters is `datacenter.discover`. Below is an example command for discovering all datacenters:

	$ vpoller-clinet -m datacenter.discover -V vc01-test.example.org -e tcp://localhost:10123

## Discovering Clusters

The method we use for discovering clusters is `cluster.discover`. Below is an example command for discovering all clusters:

	$ vpoller-clinet -m cluster.discover -V vc01-test.example.org -e tcp://localhost:10123

## Polling vSphere Object Properties

In order to get a vSphere Object property we need to send the property name of the object we are interested in.

Let's say that we want to get the power state of the ESXi host *esxi01-test.example.org* which is registered to the vCenter *vc01-test.example.org*.

	$ vpoller-client -m host.get -n esxi01-test.example.org -p runtime.powerState -V vc01-test.example.org -e tcp://localhost:10123
	
This is an example command we would execute in order to get the capacity of a datastore from our vCenter:

	$ vpoller-client -m datastore.get -n ds:///vmfs/volumes/5190e2a7-d2b7c58e-b1e2-90b11c29079d/ -p summary.capacity -V vc01-test.example.org -e tcp://localhost:10123
	
For more information about the property names you could use please refer to the [vSphere API documentation](https://www.vmware.com/support/developer/vc-sdk/).

## Getting multiple properties at once

You can also request multiple properties for an object by appending the properties separated by a comma at the command-line.

The example command below would request multiple properties to be returned for an ESXi host: 

	$ vpoller-client -m host.get -V vc01-test.example.org -e tcp://localhost:10123 -n esx01.example.org -p runtime.powerState,hardware.memorySize,summary.overallStatus

## Using the management interface of vPoller

At any time you can request status information from your vPoller Proxy or Worker by sending a request to the management socket of your `Proxy` or `Worker`.

This is how you could get status information from your vPoller Proxy:

	$ vpoller-proxy -e tcp://localhost:9999 status
	
And this is how you could get status information from your `vPoller Workers`:

	$ vpoller-worker -e tcp://localhost:10000 status
	
The management interface of `vPoller Proxy` and `Worker` also accepts commands for shutting down the components.

This is how you could shutdown your `vPoller Proxy` by sending a shutdown message to your node:

	$ vpoller-proxy -e tcp://localhost:9999 stop
	
And this is how you could shutdown your `vPoller Worker` by sending a shutdown message to your nodes:

	$ vpoller-worker -e tcp://localhost:10000 stop

You can also perform these operations using the *init.d* scripts from the vPoller Github repository.

## Bugs

Probably. If you experience a bug issue, please report it to the [vPoller issue tracker on Github](https://github.com/dnaeon/py-vpoller/issues).
