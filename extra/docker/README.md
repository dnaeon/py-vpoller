# BUILD
To build the All-in-one image just use:
~~~~
docker build . --rm --tag vpoller/vpoller-aio:xenial
~~~~
_you can use for tag whatever you want_

# RUN
To run the container type:
~~~~
docker run --rm -it --name vpoller-test vpoller/vpoller-aio:xenial
~~~~

Or if you want it persistent:
~~~~
docker run --name vpoller-aio -it vpoller/vpoller-aio:xenial
~~~~

To get a console in this container:
~~~~
docker exec --name vpoller-test -it /bin/bash
~~~~

# docker-compose
After build you also may simply use docker-compose for convenience:
~~~~
docker-compose up    # for starting up the container or with -d for detached mode
docker-compose stop  # for stopping the container
docker-compose start # for restarting the container
docker-compose down  # for deleting the container
~~~~

# CONFIG
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

For data persistency "/var/lib/vconnector" is exported. vconnector.db is created by the startup script if not present.
Also you can create an hosts.file in the volume with a host list wich is imported to the vconnector on container startup.
~~~~
hostname1;hostip1;user;password
hostname2;hostip2;user;password
~~~~
The script is also writing the hostnames for resolving to the /etc/hosts file.

You also may execute the script while running the container with:
~~~~
/import-hostsfile.sh && vconnector-cli get
~~~~
