FROM 'zabbix/zabbix-proxy-sqlite3:ubuntu-3.4-latest'

ENV ZBX_SOURCE_VERSION 3.4.14
ENV GOVC_VERSION 0.18.0

RUN set -x \
    && apt-get update && apt-get install -y --no-install-recommends git make libtool dh-autoreconf build-essential ca-certificates jq curl wget libpython3.6 \
    && cd ~ \
    && curl -L https://github.com/vmware/govmomi/releases/download/v$GOVC_VERSION/govc_linux_amd64.gz --output govc_linux_amd64.gz \
    && gunzip govc_linux_amd64.gz \
    && mv govc_linux_amd64 /usr/local/bin/govc \
    && chmod +x /usr/local/bin/govc \
    && git clone https://github.com/zeromq/zeromq4-x.git \
    && cd ~/zeromq4-x \
    && ./autogen.sh \
    && ./configure \
    && make && make install && make clean \
    && ldconfig \
    && cd ~ \
    && rm -rf ~/zeromq4-x \
    && apt-get update && apt-get remove -y git make libtool dh-autoreconf build-essential \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*

RUN set -x \
    && apt-get update && apt-get install -y --no-install-recommends python-pip python3-pip wget build-essential gcc python-dev python-setuptools python3-setuptools \
    && pip install --upgrade pip \
    && pip3 install pyzmq docopt pyVmomi vconnector \
    && apt-get update && apt-get remove -y python3-pip python-pip build-essential gcc python-dev \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*

RUN set -x \
    && apt-get update && apt-get install -y --no-install-recommends python-pip git make libtool dh-autoreconf build-essential supervisor \
    && pip install pyyaml pyzabbix \
    && cd ~ \
    && mkdir ~/builds \
    && git clone https://github.com/dnaeon/py-vpoller.git \
    && cd py-vpoller \
    && python setup.py install \
    && cd ~/py-vpoller/extra/vpoller-cclient \
    && make \
    && cp -fv vpoller-cclient ~/builds \
    && cd ~ \
    && wget https://sourceforge.net/projects/zabbix/files/ZABBIX%20Latest%20Stable/${ZBX_SOURCE_VERSION}/zabbix-${ZBX_SOURCE_VERSION}.tar.gz/download -O zabbix-${ZBX_SOURCE_VERSION}.tar.gz \
    && tar zxvf zabbix-${ZBX_SOURCE_VERSION}.tar.gz \
    && cd zabbix-${ZBX_SOURCE_VERSION} \
    && ./configure \
    && cd ~ \
    && cp -a ~/py-vpoller/extra/zabbix/vpoller-module ~/zabbix-${ZBX_SOURCE_VERSION}/src/modules \
    && cd ~/zabbix-${ZBX_SOURCE_VERSION}/src/modules/vpoller-module \
    && make \
    && cd ~ \
    && mkdir /usr/local/lib/zabbix \
    && cp ~/zabbix-${ZBX_SOURCE_VERSION}/src/modules/vpoller-module/vpoller.so ~/builds \
    && cp -afv ~/py-vpoller/extra/zabbix/vsphere-import ~/ \
    && rm -rf ~/zabbix-${ZBX_SOURCE_VERSION}.tar.gz \
    && rm -rf ~/zabbix-${ZBX_SOURCE_VERSION} \
    && rm -rf ~/py-vpoller \
    && apt-get update && apt-get remove -y git make libtool dh-autoreconf build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

RUN set -x \
    && cp -fv ~/builds/vpoller-cclient /usr/local/bin/ \
    && cp -fv ~/builds/vpoller.so /var/lib/zabbix/modules/

ENV VPOLLER_WORKER_CONCURRENCY 4

EXPOSE 10123/TCP
EXPOSE 10124/TCP
EXPOSE 9999/TCP
EXPOSE 10000/TCP
EXPOSE 10051/TCP

VOLUME ["/var/lib/vconnector"]
VOLUME ["/usr/lib/zabbix/externalscripts", "/var/lib/zabbix/enc", "/var/lib/zabbix/modules", "/var/lib/zabbix/snmptraps"]
VOLUME ["/var/lib/zabbix/ssh_keys", "/var/lib/zabbix/ssl/certs", "/var/lib/zabbix/ssl/keys", "/var/lib/zabbix/ssl/ssl_ca"]

ADD conf/etc/supervisor/ /etc/supervisor/
ADD run_vpoller_component.sh /
ADD vpoller.conf /etc/vpoller/
ADD import-hostsfile.sh /
ADD vpoller_module.conf /usr/local/etc/zabbix_proxy.conf.d/

RUN chmod 0766 /import-hostsfile.sh

ENTRYPOINT ["/bin/bash"]

CMD ["/run_vpoller_component.sh", "aio"]
