#!/usr/bin/env python
"""
ccl.py

Provides a command line interface for looking up and verifying  license
claims in media files and generating the cooresponding verification RDF.

Uses the following system exit codes:
  0 - license claim(s) verified successfully
  1 - one or more license claims do not verify
  2 - no files specified for verification
  3 - error looking up a file's verification information

In the event of a error condition exit code (> 2), the stack traceback
will be printed to stderr.

Requires Python 2.3.
"""

__id__ = "$Id$"
__version__ = "$Revision$"
__copyright__ = '(c) 2004, Creative Commons, Nathan R. Yergler'
__license__ = 'licensed under the GNU GPL2'

import sys
import optparse
import pprint

from cctag.metadata import metadata
import cctag.lookup
import cctag.const

from cctag.cli import Option, OptionParser

def config_opts():
    usage = "usage: %prog [options] filenames"
    version = "%%prog %s" % cctag.const.CCT_VERSION

    options = []

    # create the options
    options.append(Option("-d", "--display", action="store_true",
                          dest="displayOnly", default=False,
                          help="Display the license claim; do not verify.")
                   )
                          
    parser = OptionParser(
        usage=usage,
        version=version,
        option_list=options)
    
    return parser

def lookup(filename, displayOnly=False):

    # retrieve the license claim
    mdata = metadata(filename)
    claim = mdata.getClaim()

    # check if it actually exists
    if claim is None:
        # no license; bail out
        print "%s does not contain a copyright/license claim." % filename
        return None
    else:
        print "%s contains the following claim:" % filename
        print claim

        if displayOnly:
            # only displaying; bail out
            return None

    # verify the file
    try:
        if cctag.lookup.lookup(filename):
            print "Verified."
        else:
            print "Unable to verify claim."
    except:
        # an error occured while trying to verify the claim...
        # print a traceback to stderr and return the appropriate exit code
        pprint.pprint(sys.exc_info(), sys.stderr)
        sys.exit(3)
        
if __name__ == '__main__':
    parser = config_opts()
    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.error("You must supply at least one file to tag.")
        sys.exit(2)
        
    # for each file specified
    result = True
    for filename in args:
        result = result and lookup(filename, displayOnly=options.displayOnly)

    # set the exit code based on whether or not all claims were verified
    if result:
        sys.exit(0)
    else:
        sys.exit(1)
