from setuptools import setup

setup(
    name='vpoller',
    version='0.3.3',
    description='Distributed VMware vSphere API Proxy',
    long_description=open('README.rst').read(),
    author='Marin Atanasov Nikolov',
    author_email='dnaeon@gmail.com',
    license='BSD',
    url='https://github.com/dnaeon/py-vpoller',
    download_url='https://github.com/dnaeon/py-vpoller/releases',
    packages=['vpoller', 'vpoller.helpers'],
    package_dir={'': 'src'},
    scripts=[
        'src/vpoller-client',
        'src/vpoller-proxy',
        'src/vpoller-worker',
    ],
    install_requires=[
        'pyzmq >= 14.1.1',
        'docopt >= 0.6.1',
        'pyvmomi >= 5.5.0',
        'tabulate >= 0.7.2',
        'vconnector >= 0.3.0',
    ]
)
