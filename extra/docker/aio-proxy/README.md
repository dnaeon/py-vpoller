# vPoller All-In-One with Zabbix Proxy

Using the zabbix proxy instead of zabbix agent may have some benefits but as always also some drawbacks.
The biggest benefit is the ease of configuration.
If you correctly set your nameresolution you may just create an new zabbix host item with whatever item name you want and provide the real ip/dns settings in the agent fields. Then all check items may use the correct connections without troubles. No macro fiddling or dual agent adresses.

One drawback of course will be the limited features of the zabbix proxy like no computed items or custom multipliers. Well the great team of Zabbix may solve that drawback sooner than later maybe.

## BUILD

To build the all-in-one proxy image just use:

~~~~bash
./build
~~~~

You can use for tag whatever you want but for the next line we will use vpoller/vpoller:aio-proxy. Althought it is highly recommended to use a versioned tag like aio-proxy-3.4.11.
In that way you may revert after a change back to your previous image - if you just use :aio-proxy you will overwrite your images!

## RUN

To run the container type:

~~~~bash
docker run --rm -it vpoller/vpoller:aio-proxy
~~~~

Or if you want it persistent:

~~~~bash
docker run --name vpoller-proxy -it vpoller/vpoller:aio-proxy
~~~~

To get a console in this container:

~~~~bash
docker exec --name vpoller-proxy -it /bin/bash
~~~~

## CONFIG

You always may exec in the shell and use vpollers own cli.

You can use environment variables for:

- Default proxy frontend port:VPOLLER_PROXY_FRONTEND_PORT=10123
- Default proxy backend port: VPOLLER_PROXY_BACKEND_PORT=10124
- Default proxy management port: VPOLLER_PROXY_MGMT_PORT=9999
- Default worker management port: VPOLLER_WORKER_MGMT_PORT=10000
- Default worker helpers: VPOLLER_WORKER_HELPERS="vpoller.helpers.zabbix, vpoller.helpers.czabbix"
- Default worker helpers: VPOLLER_WORKER_TASKS="vpoller.vsphere.tasks"
- Default worker proxy hostname: VPOLLER_WORKER_PROXYHOSTNAME="localhost"
- Default cache enabled: VPOLLER_CACHE_ENABLED="True"
- Default cache maxsize: VPOLLER_CACHE_MAXSIZE="0"
- Default cache ttl: VPOLLER_CACHE_TTL="3600"
- Default cache housekeeping time: VPOLLER_CACHE_HOUSEKEEPING="480"
- Default worker concurrency: VPOLLER_WORKER_CONCURRENCY="4"

For data persistency "/var/lib/vconnector" is exported. vconnector.db is created by the startup script if not present.
Also you can create an hosts.file in the volume with a host list wich is imported to the vconnector on container startup.

~~~~text
hostname1;hostip1;user;password
hostname2;hostip2;user;password
~~~~

The script is also writing the hostnames for resolving to the /etc/hosts file.

You also may execute the script while running the container with:

~~~~bash
/import-hostsfile.sh && vconnector-cli get
~~~~

## Zabbix Proxy / integration

The image is based on the official Zabbix Proxy image and the components are automatically started on container start.
The vPoller Zabbix module is placed in the default module path.
If you want to use vpoller integration the zabbix proxy config file just has to contain:

~~~~text
LoadModule=vpoller.so
~~~~

If you want a module config map the agent config path and place it there

~~~~text
./zabbix_proxy.conf.d:/usr/local/etc/zabbix_proxy.conf.d/
~~~~

You may also just use Zabbix own environment variables. For example:

~~~~text
environment:
  - ZBX_SERVER_HOST=zabbix-server
  - ZBX_HOSTNAME=vpoller-proxy
  - ZBX_LOADMODULE=vpoller.so
  - ZBX_CONFIGFREQUENCY=60
  - ZBX_DATASENDERFREQUENCY=60
~~~~

### Word on zabbix host items

- To fetch data through the proxy your items have to use the "Simple check" type!

## docker-compose

After build you also may simply use docker-compose for convenience:

~~~~bash
docker-compose up    ## for starting up the container or with -d for detached mode
docker-compose stop  ## for stopping the container
docker-compose start ## for restarting the container
docker-compose down  ## for deleting the container
~~~~

The included docker-compose file assumes that you already have build the container image. It uses local directories for volume mapping.

## Versions

python 2.7.15.rc1
certifi    2018.4.16
chardet    3.0.4
docopt     0.6.2
idna       2.7
meld3      1.0.2
pip        18.0
pyvmomi    6.7.0
PyYAML     3.13
pyzabbix   0.7.4
pyzmq      17.1.0
requests   2.19.1
setuptools 39.0.1
six        1.11.0
supervisor 3.3.1
tabulate   0.8.2
urllib3    1.23
vconnector 0.5.0
vpoller    0.7.1
