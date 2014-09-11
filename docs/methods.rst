.. _methods:

============================
Supported methods by vPoller
============================

The table below lists the supported methods by vPoller along
with description for each of them.

+------------------------+--------------------------------------------------------------------------+
| vPoller Method         | Description                                                              |
+========================+==========================================================================+
| about                  | Get *about* information for a vSphere host                               |
+------------------------+--------------------------------------------------------------------------+
| event.latest           | Get the latest registered event from a vSphere host                      |
+------------------------+--------------------------------------------------------------------------+
| net.discover           | Discover all vim.Network managed objects                                 |
+------------------------+--------------------------------------------------------------------------+
| net.get                | Get properties of a vim.Network managed object                           |
+------------------------+--------------------------------------------------------------------------+
| net.host.get           | Get all HostSystems using a specific vim.Network                         |
+------------------------+--------------------------------------------------------------------------+
| net.vm.get             | Get all VirtualMachines using a specific vim.Network                     |
+------------------------+--------------------------------------------------------------------------+
| datacenter.discover    | Discover all vim.Datacenter managed objects                              |
+------------------------+--------------------------------------------------------------------------+
| datacenter.get         | Get properties of a vim.Datacenter managed object                        |
+------------------------+--------------------------------------------------------------------------+
| cluster.discover       | Discover all vim.ClusterComputeResource managed objects                  |
+------------------------+--------------------------------------------------------------------------+
| cluster.get            | Get properties of a vim.ClusterComputeResource managed object            |
+------------------------+--------------------------------------------------------------------------+
| resource.pool.discover | Discover all vim.ResourcePool managed objects                            |
+------------------------+--------------------------------------------------------------------------+
| resource.pool.get      | Get properties of a vim.ResourcePool managed object                      |
+------------------------+--------------------------------------------------------------------------+
| host.discover          | Discover all vim.HostSystem managed objects                              |
+------------------------+--------------------------------------------------------------------------+
| host.get               | Get properties of a vim.HostSystem managed object                        |
+------------------------+--------------------------------------------------------------------------+
| host.cluster.get       | Get the cluster a vim.HostSystem managed object                          |
+------------------------+--------------------------------------------------------------------------+
| host.vm.get            | Get all Virtual Machines registered on a vim.HostSystem                  |
+------------------------+--------------------------------------------------------------------------+
| host.net.get           | Get all Networks available for a specific vim.HostSystem                 |
+------------------------+--------------------------------------------------------------------------+
| host.datastore.get     | Get all datastores available to a vim.HostSystem                         |
+------------------------+--------------------------------------------------------------------------+
| vm.discover            | Discover all vim.VirtualMachine managed objects                          |
+------------------------+--------------------------------------------------------------------------+
| vm.disk.discover       | Discover all guest disks on a vim.VirtualMachine object                  |
+------------------------+--------------------------------------------------------------------------+
| vm.guest.net.get       | Discover all network adapters on a vim.VirtualMachine object             |
+------------------------+--------------------------------------------------------------------------+
| vm.net.get             | Get all Networks used by a specific vim.VirtualMachine                   |
+------------------------+--------------------------------------------------------------------------+
| vm.get                 | Get properties of a vim.VirtualMachine object                            |
+------------------------+--------------------------------------------------------------------------+
| vm.datastore.get       | Get all datastore used by a vim.VirtualMachine object                    |
+------------------------+--------------------------------------------------------------------------+
| vm.disk.get            | Get information about a guest disk for a vim.VirtualMachine object       |
+------------------------+--------------------------------------------------------------------------+
| vm.host.get            | Get the HostSystem in which a specified vim.VirtualMachine is running on |
+------------------------+--------------------------------------------------------------------------+
| vm.process.get         | Get the running processes in a vim.VirtualMachine                        |
+------------------------+--------------------------------------------------------------------------+
| vm.cpu.usage.percent   | Get the CPU usage in percentage of a Virtual Machine                     |
+------------------------+--------------------------------------------------------------------------+
| datastore.discover     | Discover all vim.Datastore objects                                       |
+------------------------+--------------------------------------------------------------------------+
| datastore.get          | Get properties of a vim.Datastore object                                 |
+------------------------+--------------------------------------------------------------------------+
| datastore.host.get     | Get all HostSystem objects using a specific datastore                    |
+------------------------+--------------------------------------------------------------------------+
| datastore.vm.get       | Get all VirtualMachine objects using a specific datastore                |
+------------------------+--------------------------------------------------------------------------+