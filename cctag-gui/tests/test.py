#!/usr/bin/env python
"""
test.py
"""

__id__ = "$Id$"
__version__ = "$Revision$"
__copyright__ = '(c) 2004, Creative Commons, Nathan R. Yergler'
__license__ = 'licensed under the GNU GPL2'

import os
import sys
import shutil
import fnmatch

import unittest

sys.path.insert(0, os.getcwd())

from cctag.metadata import metadata

class TestMp3Embedding(unittest.TestCase):
    TEST_PATTERN = '*.mp3'
    LOOK_IN = ('.', 'tests')

    LICENSE = 'http://foo/bar'
    VERIFY  = 'http://creativecommons.org'
    YEAR    = '2004'
    HOLDER  = 'nry'
    
    def setUp(self):
        # make sure we can locate the test files
        for location in self.LOOK_IN:
            if fnmatch.filter(os.listdir(os.path.join('.', location)),
                              self.TEST_PATTERN) != []:
                self._location = location
                return

    def _prepFile(self, filename):
        """Creates a copy of the specified file to
        to use for embedding tests. Returns the filename
        of the copy.
        """
        src = os.path.join('.', self._location, filename)
        dest = src.strip() + '.tmp.mp3'

        shutil.copyfile(src, dest)

        return dest
    
    def _embedFile(self, filename):
        """Embeds the specified file with dummy license info for validation.
        """
        metadata(filename).embed(self.LICENSE, self.VERIFY,
                                 self.YEAR, self.HOLDER)
        
    def _checkFile(self, filename):
        """Extracts license info from the specified file and
        returns true if it matches the set dummy info.
        """
        return (metadata(filename).getClaim() ==
                "%s %s. Licensed to the public under %s verify at %s" %
                (self.YEAR, self.HOLDER, self.LICENSE, self.VERIFY)
                )

    def _testFile(self, filename):
        tmp_file = self._prepFile(filename)
        self._embedFile(tmp_file)

        self.assert_ (self._checkFile(tmp_file),
                      "Unable to verify claim.")

    def testNoId3(self):
        self._testFile('test_id3_none.mp3')
                    
    def testId3v1(self):
        self._testFile('test_id3_1.mp3')

    def testId3v22(self):
        self._testFile('test_id3_22.mp3')

    def testId3v23(self):
        self._testFile('test_id3_23.mp3')
    
def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(TestMp3Embedding),
        ))

if __name__=='__main__':
    print os.getcwd()
    
    unittest.main(defaultTest='test_suite')
