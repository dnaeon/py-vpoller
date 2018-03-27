FROM ubuntu:xenial

ENV ZBX_CLIENT_VERSION 3.4
ENV ZBX_SOURCE_VERSION 3.4.7

RUN set -x \
	&& apt-get update && apt-get install -y --no-install-recommends python-pip supervisor wget \
    && wget http://repo.zabbix.com/zabbix/${ZBX_CLIENT_VERSION}/ubuntu/pool/main/z/zabbix-release/zabbix-release_${ZBX_CLIENT_VERSION}-1+xenial_all.deb \
    && dpkg -i zabbix-release_${ZBX_CLIENT_VERSION}-1+xenial_all.deb \
    && rm -rf zabbix-release_${ZBX_CLIENT_VERSION}-1+xenial_all.deb \
    && apt-get update && apt-get install -y zabbix-agent \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system --quiet zabbix \
    && adduser --quiet \
            --system --disabled-login \
            --ingroup zabbix \
            --home /var/lib/zabbix/ \
        zabbix \
    && pip install --upgrade pip \
    && pip install setuptools \
    && pip install pyzmq docopt pyVmomi vconnector

RUN apt-get update && apt-get install -y --no-install-recommends git make libtool dh-autoreconf build-essential \
    && cd ~ \
    && mkdir ~/builds \
    && git clone https://github.com/dnaeon/py-vpoller.git \
    && cd py-vpoller \
    && python setup.py install \
    && cd ~ \
    && git clone https://github.com/zeromq/zeromq4-x.git \
    && cd ~/zeromq4-x \
    && ./autogen.sh \
    && ./configure \
    && make && make install && make clean \
    && ldconfig \
    && cd ~/py-vpoller/extra/vpoller-cclient \
    && make \
    && cp vpoller-cclient /usr/local/bin/ \
    && cp vpoller-cclient ~/builds \
    && cd ~ \
    && wget https://sourceforge.net/projects/zabbix/files/ZABBIX%20Latest%20Stable/${ZBX_SOURCE_VERSION}/zabbix-${ZBX_SOURCE_VERSION}.tar.gz/download -O zabbix-${ZBX_SOURCE_VERSION}.tar.gz \
    && tar zxvf zabbix-${ZBX_SOURCE_VERSION}.tar.gz \
    && cd zabbix-${ZBX_SOURCE_VERSION} \
    && ./configure \
    && cp -a ~/py-vpoller/extra/zabbix/vpoller-module ~/zabbix-${ZBX_SOURCE_VERSION}/src/modules \
    && cd ~/zabbix-${ZBX_SOURCE_VERSION}/src/modules/vpoller-module \
    && make \
    && mkdir /usr/local/lib/zabbix \
    && cp ~/zabbix-${ZBX_SOURCE_VERSION}/src/modules/vpoller-module/vpoller.so /usr/local/lib/zabbix \
    && cp ~/zabbix-${ZBX_SOURCE_VERSION}/src/modules/vpoller-module/vpoller.so ~/builds \
    && rm -rf ~/zabbix-${ZBX_SOURCE_VERSION}.tar.gz \
    && rm -rf ~/zabbix-${ZBX_SOURCE_VERSION} \
    && rm -rf ~/zeromq4-x \
    && rm -rf ~/py-vpoller \
    && apt-get update && apt-get remove -y git make libtool dh-autoreconf build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

EXPOSE 10123/TCP
EXPOSE 10124/TCP
EXPOSE 9999/TCP
EXPOSE 10000/TCP

VOLUME ["/var/lib/vconnector","/etc/zabbix/zabbix_agentd.d/"]

ADD conf/etc/supervisor/ /etc/supervisor/
ADD run_vpoller_component.sh /
ADD vpoller.conf /etc/vpoller/
ADD import-hostsfile.sh /
ADD vpoller_module.conf /etc/zabbix/zabbix_agentd.d/
RUN chmod 0766 /import-hostsfile.sh

ENTRYPOINT ["/bin/bash"]

CMD ["/run_vpoller_component.sh", "aio"]
