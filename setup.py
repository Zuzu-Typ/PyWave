"""A setuptools based setup module.
See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='PyWave',
    
    version='0.3.0',

    description='Open and read Wave files',
    
    long_description=open(path.join(here, 'README.md')).read(),
    long_description_content_type='text/markdown',

    # The project's main homepage.
    url='https://github.com/Zuzu-Typ/PyWave',

    # Author details
    author='Zuzu_Typ',
    author_email='zuzu.typ@gmail.com',
    
    license='zlib/libpng license',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 5 - Production/Stable',
        
        'Intended Audience :: Developers',
        'Topic :: Games/Entertainment',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Software Development :: Libraries',
        
        'License :: OSI Approved :: zlib/libpng License',
        
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    
    keywords='WAVE RIFF wav interface simple read open',
    
    py_modules=["PyWave"],
)
