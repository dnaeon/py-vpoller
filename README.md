## vPoller -- VMware vSphere Distributed Pollers written in Python

`vPoller` is a distributed system written in Python used for discovering and polling of VMware vSphere Objects properties.

`vPoller` uses the [VMware vSphere API](https://www.vmware.com/support/developer/vc-sdk/) in order to perform discovery and polling of `Objects` from a vSphere host (e.g. ESXi or vCenter server instance).

The system consists of a number of components, each responsible for a specific task. The table below summarizes the `vPoller` components and their purpose.

| Component      | Purpose                                                                 |
|----------------|-------------------------------------------------------------------------|
| vpoller-proxy  | ZeroMQ proxy, which load-balances client requests to a pool of workers  |
| vpoller-worker | vSphere Worker, which does the discovering and polling of objects       |
| vpoller-client | Client application, used for sending and receiving requests             |

Below you can find more information about the different components along with instructions on how to install and configure them.

The distributed nature of `vPoller` is provided by the [ZeroMQ messaging library](http://zeromq.org/), which is also used to load balance client requests to a pool of vSphere Workers.

`vPoller` was designed to be easy for integration into systems which require access to vSphere Objects properties, but do not have native support for it. 

Possible scenarios where `vPoller` could be used is to integrate it into monitoring systems as part of the discovery and polling process in order to provide monitoring of your VMware vSphere environment. It could also be used in applications for collecting statistics and other metrics from your vSphere environment.

`vPoller` can also be described as a vSphere API-proxy, because it translates user requests to vSphere API requests thus allowing the user to use the API without having the need to know how the vSphere API works internally.

You could also use `vPoller` in order to navigate through your vSphere environment, thus we can also say that `vPoller` can be used as command-line navigator for your vSphere environment.

vPoller has been tested with VMware vSphere 5.x and with very limited testing on vSphere 4.x

You might also want to check this [introduction post about vPoller](http://unix-heaven.org/node/103), which contains real-world usage examples of *vPoller*.

The table below summarizes the list of currently supported methods by `vPoller` along with description for each of them.

| vPoller Method         | Description                                                              |
|------------------------|--------------------------------------------------------------------------|
| about                  | Get 'about' information for the vSphere host this agent is connected to  |
| event.latest           | Get the latest registered in the vSphere host the agent is connected to  |
| net.discover           | Discover all vim.Network managed objects                                 |
| net.get                | Get properties for a vim.Network managed object                          |
| net.host.get           | Get all HostSystems using a specified vim.Network                        |
| net.vm.get             | Get all VirtualMachines using a specified vim.Network                    |
| datacenter.discover    | Discover all vim.Datacenter managed objects                              |
| datacenter.get         | Get properties for a vim.Datacenter managed object                       |
| cluster.discover       | Discover all vim.ClusterComputeResource managed objects                  |
| cluster.get            | Get properties for a vim.ClusterComputeResource managed object           |
| resource.pool.discover | Discover all vim.ResourcePool managed objects                            |
| resource.pool.get      | Get properties for a vim.ResourcePool managed object                     |
| host.discover          | Discover all vim.HostSystem managed objects                              |
| host.get               | Get properties for a vim.HostSystem managed object                       |
| host.cluster.get       | Get the cluster name for a vim.HostSystem managed object                 |
| host.vm.get            | Get all Virtual Machines running on a specified vim.HostSystem           |
| host.net.get           | Get all Networks available for a specified vim.HostSystem                |
| host.datastore.get     | Get all datastores available to a vim.HostSystem                         |
| vm.discover            | Discover all vim.VirtualMachine managed objects                          |
| vm.disk.discover       | Discover all guest disks on a vim.VirtualMachine object                  |
| vm.guest.net.get       | Discover all network adapters on a vim.VirtualMachine object             |
| vm.net.get             | Get all Networks used by a specified vim.VirtualMachine                  |
| vm.get                 | Get properties for a vim.VirtualMachine object                           |
| vm.datastore.get       | Get all datastore used by a vim.VirtualMachine object                    |
| vm.disk.get            | Get information about a guest disk for a vim.VirtualMachine object       |
| vm.host.get            | Get the HostSystem in which a specified vim.VirtualMachine is running on |
| vm.process.get         | Get the running processes in a vim.VirtualMachine                        |
| datastore.discover     | Discover all vim.Datastore objects                                       |
| datastore.get          | Get properties for a vim.Datastore object                                |

## Requirements

* Python 2.7.x
* [pyVmomi](https://github.com/vmware/pyvmomi)
* [pyzmq](https://github.com/zeromq/pyzmq)
* [docopt](https://github.com/docopt/docopt)
* [tabulate](https://pypi.python.org/pypi/tabulate)

The C client of *vPoller* also requires the following packages to be installed in order to build it:

* Python development files (on Debian systems this is usually provided by the *python-dev* package)
* [ZeroMQ 4.x Library](https://github.com/zeromq/zeromq4-x)

## Contributions

*vPoller* is hosted on Github. Please contribute by reporting issues, suggesting features or by sending patches using pull requests.

## Installation

In order to install *vPoller* simply execute the command below:

	$ sudo python setup.py install

If you would like to install `vPoller` in a `virtualenv` execute these commands instead:

	$ virtualenv vpoller-venv
	$ source vpoller-venv/bin/activate
	$ cd /path/to/py-vpoller
	$ python setup.py install

This should take care of installing all the dependencies for you as well.

We need to create a few directories as well, which are used by the `vPoller` components to store their log files and other data, so make sure you create them first:

	$ sudo mkdir /var/lib/vconnector /var/log/vpoller
	
Future versions of `vPoller` will probably provide ready to use packages, so this will be taken care of at that stage as well.

And that's it with the installation. Now go ahead to the next section which explains how to configure the vPoller components.

## Configuration

The default configuration file of `vPoller` resides in `/etc/vpoller/vpoller.conf` file.

Below is an example `vpoller.conf` file:

	[proxy]
	frontend = tcp://*:10123
	backend  = tcp://*:10124
	mgmt     = tcp://*:9999

	[worker]
	db       = /var/lib/vconnector/vconnector.db
	proxy    = tcp://localhost:10124
	mgmt     = tcp://*:10000

The table below provides information about the config entries used along with a description for each of them.

| Section | Option    | Description                                                                       |
|---------|-----------|-----------------------------------------------------------------------------------|
| proxy   | frontend  | Endpoint to which clients connect and send their requests to                      |
| proxy   | backend   | Endpoint to which `vPoller Workers` connect and get requests for processing       |
| proxy   | mgmt      | Management endpoint, used for sending management messages to the `vPoller Proxy`  |
| worker  | db        | Path to the `vSphere Agents` SQLite database file                                 |
| worker  | proxy     | Endpoint to the `vPoller Proxy` backend to which the `vPoller Worker` connects    |
| worker  | mgmt      | Management endpoint, used for sending management messages to the `vPoller Worker` |

Next thing we need to do is configure our `vSphere Agents`. The `vSphere Agents` are the ones that take care of establishing
connection to the vSphere hosts and do the actual discovery and polling of vSphere Object properties.

Details of the `vSphere Agents` (such as username, password, host, etc.) are stored in a SQLite database and are managed by the
`vconnector-cli` tool. By default the SQLite database file used by `vconnector-cli` resides in `/var/lib/vconnector/vconnector.db`.

Let's add one `vSphere Agent`, which will later be used by the `vPoller Worker`. This is how we could do it using the `vconnector-cli` tool:

	$ sudo vconnector-cli -H vc01.example.org -U root -P p4ssw0rd add

Make sure you enable the `vSphere Agent`, otherwise it will not be used by the `vPoller Worker`:

	$ sudo vconnector-cli -H vc01.example.org enable

At any time you can view the currently registered `vSphere Agents` by running the `vconnector-cli get` command, e.g.:

	$ sudo vconnector-cli get

	+--------------+---------------------+-------------+-----------+
	| Hostname     | Username            | Password    |   Enabled |
	+==============+=====================+=============+===========+
	| vc01         | root                | p4ssw0rd    |         1 |
	+--------------+---------------------+-------------+-----------+

Also make sure that this file is readable only by the user/group you run `vPoller` as, so you don't want to expose any sensitive data to users.

## Starting vPoller components

Once you configure the `vPoller` components and register all `vSphere Agents` you intend to run we can start up everything.

In order to start `vPoller Proxy` execute the command below:

	$ sudo vpoller-proxy start

In order to start `vPoller Worker` execute the command below:

	$ sudo vpoller-worker start

Usually you would want to have more than one `vPoller Worker` connected to the `vPoller Proxy` in order to provide redundancy and scalability.

**NOTE**: You can also use the `init.d` scripts in the repo for starting up `vPoller Proxy` and `vPoller Worker` components, which is probably what you would want to run during boot-time.

Run the commands below in order to get help and usage information:
	
	$ vpoller-proxy --help
	$ vpoller-worker --help
	
Checking the log files at `/var/log/vpoller` should indicate that everything started up successfully or contain errors in case something went wrong. 

## Examples

The `vPoller Client` is the client application used for sending requests to the `vPoller Workers`.

Considering that you have the `vPoller` components configured and started up we will now see how to send example requests to
`vPoller` in order to perform discovery and polling of vSphere object properties.

The tool that we will use in all these examples below is `vpoller-client`. In order to get help and usage information at any time execute the command below:

	$ vpoller-client --help

Check the examples below which show how to use `vpoller-client` in order to send client requests to `vPoller`.

## Discovering objects examples

This section provides examples for discovery of vSphere objects using `vPoller`.

Example command to discover all `Datacenter` managed objects:

	$ vpoller-client -m datacenter.discover -V vc01.example.org

Example command to discover all `ClusterComputeResource` managed objects:

	$ vpoller-clinet -m cluster.discover -V vc01.example.org

Example command to discover all `HostSystem` managed objects:

	$ vpoller-client -m host.discover -V vc01.example.org

Example command to discover all `Datastore` managed objects:

	$ vpoller-client -m datastore.discover -V vc01.example.org

Example command to discover all `VirtualMachine` managed objects:

	$ vpoller-client -m vm.discover -V vc01.example.org

Example command to discover all disks in a `VirtualMachine` managed object:

	$ vpoller-client -m vm.disk.discover -V vc01.example.org -n vm01.example.org

For other methods you could use please refer to the table of supported vPoller methods.

For more information about the property names you could use please refer to the [vSphere API documentation](https://www.vmware.com/support/developer/vc-sdk/).

## Polling object properties examples

This section provides examples for polling vSphere object properties using `vPoller`:

Example command to get the `powerState` property of a `HostSystem` (ESXi host) managed object:

	$ vpoller-client -m host.get -n esxi01.example.org -p runtime.powerState -V vc01.example.org

Example command to get the `capacity` of a `Datastore` managed object:

	$ vpoller-client -m datastore.get -n ds:///vmfs/volumes/5190e2a7-d2b7c58e-b1e2-90b11c29079d/ -p summary.capacity -V vc01.example.org

Example command to get information about disks in a `VirtualMachine` managed objects:

	$ vpoller-client -m vm.disk.get -n vm01.example.org -V vc01.example.org -k /var

Example command to get all `VirtualMachines` running on a `HostSystem` (ESXi host):

	$ vpoller-client -m host.vm.get -n esxi01.example.org -V vc01.example.org

Example command to get the `HostSystem` on which a `VirtualMachine` is running:

	$ vpoller-client -m vm.host.get -n vm01.example.org -V vc01.example.org

For other methods you could use please refer to the table of supported vPoller methods.

For more information about the property names you could use please refer to the [vSphere API documentation](https://www.vmware.com/support/developer/vc-sdk/).

## Getting multiple properties at once

You can also request multiple properties for an object by appending the properties separated by a comma at the command-line.

The example command below would request multiple properties to be returned for a `HostSystem` (ESXi host) managed object: 

	$ vpoller-client -m host.get -V vc01.example.org -n esx01.example.org -p runtime.powerState,hardware.memorySize,summary.overallStatus

## vPoller Helpers

The `vPoller Helpers` were implemented in order to provide an easy way for connecting your applications to `vPoller`.

The table below summarizes the currently existing and supported `vPoller Helpers`:

| vPoller Helper            | Description                                          |
|---------------------------|------------------------------------------------------|
| vpoller.helpers.zabbix    | Helper which returns data in Zabbix-friendly format  |
| vpoller.helpers.csvhelper | Helper which returns data in CSV format              |

The result messages returned by a `vPoller Worker` are always in JSON format. 

This could be okay for most applications, which require to process a result message, but in some cases you might want to
receive the result in different formats and feed the data into your application. 

Using the `vPoller Helpers` you are able to convert the result message to a format that your application or system understands.

An example of such a `vPoller Helper` is the [Zabbix vPoller Helper module](https://github.com/dnaeon/py-vpoller/tree/master/src/vpoller/helpers), which can
translate a result message to [Zabbix LLD format](https://www.zabbix.com/documentation/2.2/manual/discovery/low_level_discovery) and return
property values ready to be used in Zabbix items.

Here is an example of using the `Zabbix vPoller Helper` for converting the result to `Zabbix LLD format`:

	$ vpoller-client -H vpoller.helpers.zabbix -m datastore.discover -V vc01.example.org
	
This is how you could use the `vpoller.helpers.zabbix` helper to retrieve a property of a vSphere Object.

	$ vpoller-client -H vpoller.helpers.zabbix -m datastore.get -V vc01.example.org -n <datastore-url> -p summary.capacity
	
This would return just the value of the property requested, thus making it easy for integrating the result into a `Zabbix Item`.

Possible other usage of the `vPoller Helpers` is an HTML helper, which would return the result in HTML format in order to present the information nicely in a web browser.

## Using the management interfaces of vPoller

At any time you can request status information from your `vPoller Proxy` or `Worker` by sending a request to the management endpoints:

This is how you could get status information from your `vPoller Proxy`:

	$ vpoller-proxy -e tcp://localhost:9999 status
	
And this is how you could get status information from your `vPoller Workers`:

	$ vpoller-worker -e tcp://localhost:10000 status
	
The management interface of `vPoller Proxy` and `Worker` also accepts commands for shutting down the components.

This is how you could shutdown your `vPoller Proxy` by sending a shutdown message to your node:

	$ vpoller-proxy -e tcp://localhost:9999 stop
	
And this is how you could shutdown your `vPoller Worker` by sending a shutdown message to your nodes:

	$ vpoller-worker -e tcp://localhost:10000 stop

You can also perform these operations using the `init.d` scripts from the vPoller Github repository.

## Bugs

Probably. If you experience a bug issue, please report it to the [vPoller issue tracker on Github](https://github.com/dnaeon/py-vpoller/issues).
