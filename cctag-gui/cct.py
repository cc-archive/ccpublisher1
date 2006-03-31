#!/usr/bin/env python
"""
cct.py

Provides a command line interface for embedding license claims in
media files and generating the cooresponding verification RDF.

Uses the following system exit codes:
  0 - embedded successfuly, verification RDF printed to stdout
  1 - no files specified for embedding
  2 - error embedding license information
  3 - error generating verification RDF

In the event of a error condition exit code (> 1), the stack traceback
will be printed to stderr.

Requires Python 2.3.
"""

__id__ = "$Id$"
__version__ = "$Revision$"
__copyright__ = '(c) 2004, Creative Commons, Nathan R. Yergler'
__license__ = 'licensed under the GNU GPL2'

import sys
import os
import optparse
import traceback

from cctag.metadata import metadata
import cctag.rdf as rdf
import cctag.const
import cctag.lookup

from cctag.cli import Option, OptionParser

def config_opts():
    usage = "usage: %prog [options] filenames"
    version = "%%prog %s" % cctag.const.CCT_VERSION

    options = []

    # create the options
    options.append(Option("-o", "--holder", type="string", dest="holder",
                          help="The copyright holder for the files",
                          required=True
                          )
                    )
    options.append(Option("-y", "--year", type="int", dest="year",
                          help="The copyright year for the files",
                          required=True
                          )
                   )
    options.append(Option("-l", "--license", type="string", dest="license",
                          help="URL of the embedded license",
                          required=True
                          )
                   )
    options.append(Option("-v", "--validation", type="string",
                          dest="validation", required=True,
                          help="Validation URL for this file",
                          )
                   )

    parser = OptionParser(
        usage=usage,
        version=version,
        option_list=options)
    
    return parser

def embed(options, files):
    # get option values
    license = options.license
    verify_url = options.validation
    year = options.year
    holder = options.holder

    # embed the specified license in each file
    for filename in files:
        try:
            metadata(filename).embed(license, verify_url, str(year), holder)
        except:
            pprint.pprint(sys.exc_info(), sys.stderr)
            sys.exit(2)

    # generate the verification RDF
    try:
        verification = rdf.generate(files, verify_url, 
                                license, str(year), holder)
    except:
        traceback.print_exc()
        sys.exit(3)

    return verification

if __name__ == '__main__':
    parser = config_opts()
    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.error("You must supply at least one file to tag.")
        sys.exit(1)

    if not validateOptions(options):
        parser.error("You must supply either a copyright holder, year, "
                     "license URL and \nverification URL.")
        sys.exit(1)
        
    print embed(options, args)
    sys.exit(0)
