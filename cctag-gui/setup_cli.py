"""
CC Command Line Tools build script
Builds platform appropriate packages for distribution.

Nathan R. Yergler

$Id$
"""

import os
import sys
import shutil
import fnmatch

from distutils.core import setup
from cctag.const import CCT_VERSION

# check for win32 support
if sys.platform == 'win32':
    # win32 allows building of executables
    import py2exe

# call the standard distutils builder for the CLI apps 
setup(name='cc_cli_tools',
      version=CCT_VERSION,
      url='http://creativecommons.org',
      author='Nathan R. Yergler',
      author_email='nathan@creativecommons.org',
      py_modules=['cct','ccl','claim'],
      scripts=['cct.py', 'ccl.py', 'claim.py'],
      console=['cct.py', 'ccl.py', 'claim.py'],
      packages=['cctag', 'tagger', 'ccrdf', 
                'rdflib', 'rdflib.syntax',
                'rdflib.syntax.serializers', 'rdflib.syntax.parsers',
                'rdflib.backends', 'rdflib.model',],
      )

