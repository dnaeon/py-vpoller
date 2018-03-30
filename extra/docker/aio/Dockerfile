FROM 'zabbix/zabbix-agent:ubuntu-3.4.7'

ENV ZBX_SOURCE_VERSION 3.4.7

RUN set -x \
    && apt-get update && apt-get install -y --no-install-recommends git make libtool dh-autoreconf build-essential ca-certificates \
    && cd ~ \
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
    && apt-get update && apt-get install -y --no-install-recommends python-pip wget build-essential gcc python-dev \
    && pip install --upgrade pip \
    && pip install --upgrade setuptools \
    && pip install pyzmq docopt pyVmomi vconnector \
    && apt-get update && apt-get remove -y python-pip build-essential gcc python-dev \
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

EXPOSE 10123/TCP
EXPOSE 10124/TCP
EXPOSE 9999/TCP
EXPOSE 10000/TCP
EXPOSE 10050/TCP

VOLUME ["/var/lib/vconnector","/etc/zabbix/zabbix_agentd.d/"]

ADD conf/etc/supervisor/ /etc/supervisor/
ADD run_vpoller_component.sh /
ADD vpoller.conf /etc/vpoller/
ADD import-hostsfile.sh /
ADD vpoller_module.conf /etc/zabbix/zabbix_agentd.d/
RUN chmod 0766 /import-hostsfile.sh

ENTRYPOINT ["/bin/bash"]

CMD ["/run_vpoller_component.sh", "aio"]
