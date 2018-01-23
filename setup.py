import os
from setuptools import setup
from codecs import open

# http://setuptools.readthedocs.io/en/latest/setuptools.html

here = os.path.abspath(os.path.dirname(__file__))

with open('README.md', 'r', 'utf-8') as f:
    readme = f.read()


about = {}
with open(os.path.join(here, 'app', '__version__.py'), 'r', 'utf-8') as f:
    exec(f.read(), about)

setup(name=about['__title__'],
      version=about['__version__'],
      description=about['__description__'],
      url=about['__url__'],
      author=about['__author__'],
      author_email=about['__author_email__'],
      license=about['__license__'],
      long_description=readme,
      keywords="broken links check checker invalid urls url",
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
