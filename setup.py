import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


# http://setuptools.readthedocs.io/en/latest/setuptools.html

setup(name='checklinks',
      version='0.2',
      description='Fetch, find and report broken links on all pages of a website.',
      url='https://gitlab.com/alexbenfica/check-links/',
      author='Alex Benfica',
      author_email='alexbenfica@gmail.com',
      keywords="broken links check checker invalid urls url",
      long_description=read('README.md'),
      license='MIT',
      packages=['checklinks'],
      package_dir={'checklinks': 'app'},
      install_requires=[
            'requests',
            'markdown',
            'bs4',
            'colorama'
            ],
      zip_safe=False,
      )