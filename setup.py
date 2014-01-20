from distutils.core import setup

setup(name='py-vpoller',
      version='0.1.1',
      description='VMware vSphere Distributed Pollers',
      author='Marin Atanasov Nikolov',
      author_email='dnaeon@gmail.com',
      license='BSD',
      packages=['vpoller', 'vpoller.helpers'],
      package_dir={'': 'src'},
      scripts=[
        'src/vpoller-client',
        'src/vpoller-proxy',
        'src/vpoller-worker'
      ],
      install_requires=[
        'pysphere >= 0.1.8',
        'vconnector >= 0.1.0',
        'pyzmq >= 13.1.0',
        'docopt >= 0.6.1',
      ]
)
