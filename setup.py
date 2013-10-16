from distutils.core import setup

setup(name='vmware-zabbix',
      version='1.0.0',
      description='VMware poller module for integration with Zabbix',
      author='Marin Atanasov Nikolov',
      author_email='dnaeon@gmail.com',
      license='BSD',
      packages=['vmpoller'],
      package_dir={'': 'src'},
      scripts=[
        'src/vmpoller-client',
        'src/vmpoller-proxy',
        'src/vmpoller-worker'
      ],
      install_requires=[
        'pysphere >= 0.1.8',
        'vmconnector >= 1.0.0',
        'pyzmq >= 13.1.0',
        'docopt >= 0.6.1',
      ]
)
