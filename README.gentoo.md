## Dependencies:

- Make sure you have python 2.7 installed on your system

- Unmask the following packages:

net-libs/zeromq
dev-libs/libsodium (required for version 4.x of zeromq)
dev-python/docopt
dev-python/tabulate

- Emerge the packages:

emerge pyzmq docopt tabulate zeromq jq

- Switch to python 2.7 to install the manually requirements for the right python or use the right python binary.

- Install pyVmomi

git clone https://github.com/vmware/pyvmomi.git

cd pyvmomi
python2.7 setup.py install

- Install pv-vconnector

git clone https://github.com/dnaeon/py-vconnector.git

cd py-vconnector
python2.7 setup.py install

- Create needed directories:

mkdir /var/lib/vconnector /var/log/vpoller /var/log/vconnector /etc/vpoller /var/run/vpoller

- Install py-vpoller

git clone https://github.com/blackcobra1973/py-vpoller.git

cd py-vpoller
python2.7 setup.py install

cp src/conf/vpoller.conf /etc/vpoller/

- Compile the c-client

cd src/vpoller-cclient/
make
mv vpoller-cclient /usr/local/bin/

- Install init scripts

cp src/init.d/vpoller-proxy.gentoo /etc/init.d/vpoller-proxy
cp src/init.d/vpoller-worker.gentoo /etc/init.d/vpoller-worker

- Install the logrotate template

cp src/logrotate.d/vpoller /etc/logrotate.d/
