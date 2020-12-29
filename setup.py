from ifsm import __version__
from setuptools import setup, find_packages
import sys

long_description = "a sample fsm"

extra_kwargs = {}
if sys.version_info < (2, 7):
    extra_kwargs['setup_requires'] = []
    extra_kwargs['install_requires'] = []
if sys.version_info >= (3,):
    extra_kwargs['setup_requires'] = []

setup(
    name="ifsm",
    version=__version__,
    author="Gaoda",
    author_email="gdnhm@qq.com",
    url='https://github.com/diaohaha/ifsm',
    description='fsm',
    long_description=long_description,
    license='BSD',
    packages=find_packages(),
    platforms=['any'],
    **extra_kwargs
)