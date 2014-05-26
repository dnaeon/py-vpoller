#!/usr/bin/env sh

# Bootstrap script for one-time setup of vPoller on Debian GNU/Linux systems
# The script installs dependencies into system-wide locations

set -e

apt-get update
apt-get -y install gcc g++ git automake autoconf libtool python-pip python-dev
apt-get -y autoremove

# Install libzmq
libzmq_dir=$( mktemp -d /tmp/libzmq.XXXXXX )
echo ">>> Installing libzmq ..."
git clone https://github.com/zeromq/zeromq4-x.git ${libzmq_dir}
cd ${libzmq_dir}
./autogen.sh
./configure
make && make install && make clean
ldconfig

# Installing vConnector
vconnector_dir=$( mktemp -d /tmp/vconnector.XXXXXX )
echo ">>> Installing vConnector ..."
git clone https://github.com/dnaeon/py-vconnector.git ${vconnector_dir}
cd ${vconnector_dir}
python setup.py install

# Installing vPoller
vpoller_dir=$( mktemp -d /tmp/vpoller.XXXXXX )
echo ">>> Installing vPoller ..."
git clone https://github.com/dnaeon/py-vpoller.git ${vpoller_dir}
cd ${vpoller_dir}
python setup.py install

echo ">>> Building vPoller C Client ..."
cd src/vpoller-cclient
make && install vpoller-cclient /usr/local/bin

echo ">>> Setting up init.d scripts ..."
cd ${vpoller_dir}
install src/init.d/vpoller-proxy /etc/init.d
install src/init.d/vpoller-worker /etc/init.d
update-rc.d vpoller-proxy defaults
update-rc.d vpoller-worker defaults

# Configuring vPoller
echo ">>> Configuring vPoller ..."
mkdir -p /etc/vpoller /var/run/vpoller /var/log/vpoller /var/lib/vconnector /var/log/vconnector

cat > /etc/vpoller/vpoller.conf <<__EOF__
[proxy]
frontend = tcp://*:10123
backend  = tcp://*:10124
mgmt     = tcp://*:9999

[worker]
db       = /var/lib/vconnector/vconnector.db
proxy    = tcp://localhost:10124
mgmt     = tcp://*:10000
__EOF__

echo ">>> Initializing vConnector database ..."
vconnector-cli init

# Post-install
echo ">>> Removing no longer needed directories ..."
rm -rf ${libzmq_dir}
rm -rf ${vpoller_dir}
rm -rf ${vconnector_dir}

echo ""
echo ">>> Install completed"
echo ">>> vPoller has been installed and configured"
echo ""
echo ">>> In order to add and enable a vSphere host execute the command below:"
echo "    $ sudo vconnector-cli -H vc01.example.org -U username -P password add"
echo "    $ sudo vconnector-cli -H vc01.example.org enable"
echo ""
echo ">>> Start vPoller Proxy:"
echo "    $ sudo service vpoller-proxy start"
echo ""
echo ">>> Start vPoller Worker:"
echo "    $ sudo service vpoller-worker start"
echo ""
echo ">>> Example vPoller request to discover all ESXi hosts:"
echo "    $ vpoller-client -m host.discover -V vc01.example.org"
echo ""
echo ">>> Check the log files at /var/log/vpoller"
echo ""
echo ">>> For any issues or bugs please submit a ticket at the vPoller issue tracker:"
echo "    https://github.com/dnaeon/py-vpoller/issues"
echo ""
