#!/usr/bin/env python
"""
claim.py

Provides a command line interface for embedding license claims in
media files.

Uses the following system exit codes:
  0 - embedded successfuly, verification RDF printed to stdout
  1 - no files specified for embedding
  2 - error embedding license information

In the event of a error condition exit code (> 1), the stack traceback
will be printed to stderr.

Requires Python 2.3.
"""

__id__ = "$Id$"
__version__ = "$Revision$"
__copyright__ = '(c) 2004, Creative Commons, Nathan R. Yergler'
__license__ = 'licensed under the GNU GPL2'

import sys
import optparse
import traceback

from cctag.metadata import metadata
import cctag.const

import cctag.cli
from cctag.cli import Option, OptionParser

def config_opts():
    usage = "usage: %prog [options] filenames"
    version = "%%prog %s" % cctag.const.CCT_VERSION

    options = []

    options.append(Option("-t", "--tcop", type="string",
                          dest="tcop", required=True,
                          help="Complete copyright statement to embed."
                          )
                   )

    parser = OptionParser(
        usage=usage,
        version=version,
        option_list=options)
    
    return parser

def embed(tcop, files):
    # embed the specified claim in each file
    for filename in files:
        try:
            metadata(filename).setClaim(tcop)
        except:
            traceback.print_exc()
            sys.exit(2)

if __name__ == '__main__':
    parser = config_opts()
    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.error("You must supply at least one file to tag.")
        sys.exit(1)

    embed(options.tcop, cctag.cli.expandFiles(args))
    sys.exit(0)
