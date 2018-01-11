FROM ubuntu:xenial

RUN set -x \
	&& apt-get update && apt-get install -y --no-install-recommends python-pip supervisor \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && pip install setuptools \
    && pip install pyzmq docopt pyVmomi vconnector

RUN apt-get update && apt-get install -y --no-install-recommends git make libtool dh-autoreconf build-essential \
    && cd ~ \
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
    && rm -rf ~/zeromq4-x \
    && rm -rf ~/py-vpoller \
    && apt-get update && apt-get remove -y git make libtool dh-autoreconf build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

EXPOSE 10123/TCP
EXPOSE 10124/TCP
EXPOSE 9999/TCP
EXPOSE 10000/TCP

VOLUME ["/var/lib/vconnector"]

ADD conf/etc/supervisor/ /etc/supervisor/
ADD run_vpoller_component.sh /
ADD vpoller.conf /etc/vpoller/
ADD import-hostsfile.sh /
RUN chmod 0766 /import-hostsfile.sh

ENTRYPOINT ["/bin/bash"]

CMD ["/run_vpoller_component.sh", "aio"]
