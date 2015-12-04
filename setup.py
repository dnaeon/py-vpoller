import re
import ast

from setuptools import setup, find_packages


_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('src/vpoller/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1))
    )

setup(
    name='vpoller',
    version=version,
    description='Distributed VMware vSphere API Proxy',
    long_description=open('README.rst').read(),
    author='Marin Atanasov Nikolov',
    author_email='dnaeon@gmail.com',
    license='BSD',
    url='https://github.com/dnaeon/py-vpoller',
    download_url='https://github.com/dnaeon/py-vpoller/releases',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    scripts=[
        'src/vpoller-client',
        'src/vpoller-proxy',
        'src/vpoller-worker',
    ],
    install_requires=[
        'pyzmq >= 14.3.1',
        'docopt >= 0.6.2',
        'pyvmomi >= 6.0.0',
        'vconnector >= 0.4.3',
    ]
)
