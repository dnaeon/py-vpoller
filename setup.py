from setuptools import setup

setup(name='vpoller',
      version='0.2.0',
      description='VMware vSphere Distributed Pollers',
      author='Marin Atanasov Nikolov',
      author_email='dnaeon@gmail.com',
      license='BSD',
      packages=['vpoller', 'vpoller.helpers'],
      package_dir={'': 'src'},
      scripts=[
        'src/vpoller-client',
        'src/vpoller-proxy',
        'src/vpoller-worker',
        'src/vconnector-cli',
      ],
      install_requires=[
        'pyzmq >= 14.1.1',
        'docopt >= 0.6.1',
        'pyvmomi >= 5.5.0',
        'tabulate >= 0.7.2',  
      ]
)
