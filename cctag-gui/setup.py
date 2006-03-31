"""
ccTag build script
Builds platform appropriate packages for distribution.  Takes standard
distutils commands on non-Mac OS X platforms.  Builds a .app on Mac OS X.

Nathan R. Yergler

$Id$
"""

import os
import sys
import shutil
import fnmatch

from distutils.core import setup
from cctag.const import CCT_VERSION

CMD_BUNDLE = "build_app"
packageroot = "."

def cleanManifest():
    try:
        os.remove('MANIFEST')
    except:
        pass
    
def makeDmg(files, target):
    """Creates a mountable disk image containing the specified files on
    Mac OS X.
    """

    tmp_dir = './build/Publisher'
    
    # create a temporary folder
    if os.path.exists(tmp_dir):
       os.rmdir(tmp_dir)
    os.mkdir(tmp_dir)
    
    # copy source files to that folder
    for filename in files:
        path, orig_filename = os.path.split(filename)

        print filename
        print os.path.join(tmp_dir, orig_filename)
        if orig_filename != '':
           shutil.copytree(filename, os.path.join(tmp_dir, orig_filename))
        
    # invoke the creation command
    os.system("./make_dmg.sh")

def addLibs(app):
    """Add the wxPython library dependencies to the AppBuilder object app."""
    import wx

    # wxPython
    libdir = '/usr/local/lib/wxPython-%s/lib' % wx.__version__
    alllibs = os.listdir(libdir)
    
    for dylib in fnmatch.filter(alllibs, "*.dylib"):
        app.libs.append(os.path.join(libdir, dylib))
        
    for rsrc in fnmatch.filter(alllibs, "*.rsrc"):
        app.libs.append(os.path.join(libdir, rsrc))

    # libxml / libxslt
    libdir = '/usr/local/lib/'
    alllibs = os.listdir(libdir)
    
    for dylib in fnmatch.filter(alllibs, "libxml*.dylib"):
        app.libs.append(os.path.join(libdir, dylib))
        
    for dylib in fnmatch.filter(alllibs, "libxslt*.dylib"):
        app.libs.append(os.path.join(libdir, dylib))

# find out if we want to build a Mac OS X bundle (.app)
if CMD_BUNDLE in sys.argv:
    # remove the argument so we can also process other distutil commands
    sys.argv.remove(CMD_BUNDLE)

    # make sure this is Mac OS X
    if sys.platform != 'darwin':
        print "ERROR: You can not build a bundle on non-Mac OS X systems."

    else:
        # build the bundle
        import bundlebuilder

        # assume the build script is run from the CVS repository layout;
        # fixup the Python path accordingly so we can find modules
        sys.path.insert(1, os.getcwd())

        # Create the AppBuilder
        cctag = bundlebuilder.AppBuilder(verbosity=1)

        # Tell it where to find the main script - the one that loads on startup
        cctag.mainprogram = os.path.join(packageroot, "cctag-wiz.py")

        cctag.semi_standalone = 1
        cctag.argv_emulation = 1
        cctag.name = "ccPublisher"
        cctag.iconfile = os.path.join('resources', 'cc.icns')
        
        # set packages to include; need encodings for unicode support
        cctag.includePackages.append("encodings")
        cctag.includePackages.append("cctag")
        cctag.includePackages.append("rdflib")
        cctag.includePackages.append("ccrdf")
        cctag.includePackages.append("pyarchive")
        cctag.includePackages.append("ccwx")


        # need argvemulator to get files that are dropped onto the icon
        cctag.includeModules.append('argvemulator')

        # include the command line interface for fun
        cctag.includeModules.append('cct')
        cctag.includeModules.append('ccl')
        cctag.includeModules.append('claim')

        # add supporting files (XRC, etc)
        cctag.resources.append(os.path.join(packageroot, "cctag.xrc"))
        cctag.resources.append(os.path.join(packageroot, "wizard.xrc"))
        cctag.resources.append(os.path.join(packageroot, 'resources', 'cc_33.png'))
        cctag.resources.append(os.path.join(packageroot, 'resources', 'bullet.xpm'))
        cctag.resources.append(os.path.join(packageroot,
                                            'resources',
                                            'publishguy_small.gif')
                               )

        # add wxPython libraries
        addLibs(cctag)

        # clean the manifest
        cleanManifest()
        
        # build the app bundle
        cctag.setup()
        cctag.build()

        # create a disk image
        makeDmg([os.path.join('build', 'ccPublisher.app')],
                os.path.join('build', 'Publisher.dmg'))

# see if there's anything else to do
if len(sys.argv) == 1:
   sys.exit(0)

# check for win32 support
if sys.platform == 'win32':
    # win32 allows building of executables
    import py2exe

# call the standard distutils builder for the GUI app
cleanManifest()
setup(name='ccTag',
      version=CCT_VERSION,
      url='http://creativecommons.org',
      author='Nathan R. Yergler',
      author_email='nathan@yergler.net',
      py_modules=['cctag','cct', 'ccl', 'claim'],
      data_files=[
    ('resources', ['cctag.xrc', os.path.join('resources', 'cc.ico')]),
    ('', [os.path.join('resources', 'bullet.xpm')]),
    ],
      console=[{'script':'cct.py',
                'icon_resources':[(1, os.path.join('resources','cc.ico'))]
                },
               {'script':'ccl.py',
                'icon_resources':[(1, os.path.join('resources','cc.ico'))]
                },
               ],
      windows=[{'script':'cctag.py',
                'icon_resources':[(1, os.path.join('resources','cc.ico'))]
               }],
      scripts=['cctag.py', 'cct.py', 'ccl.py', 'claim.py'],

      packages=['cctag', 'tagger', 'ccrdf',
                'rdflib', 'rdflib.syntax',
                'rdflib.syntax.serializers', 'rdflib.syntax.parsers',
                'rdflib.backends', 'rdflib.model',],
      options={"py2exe": {"packages": ["encodings", 'rdflib'],
                          "includes": ["dumbdbm"], },
               },
      )

# call the standard distutils builder for the wizard app
cleanManifest()
setup(name='Publisher',
      version=CCT_VERSION,
      url='http://creativecommons.org',
      author='Nathan R. Yergler',
      author_email='nathan@yergler.net',
      py_modules=['cctag','cct', 'ccl', 'claim', 'html'],
      data_files=[
    ('resources', ['wizard.xrc',
                   os.path.join('resources', 'cc_33.png'),
                   os.path.join('resources', 'cc.ico'),
                   os.path.join('resources', 'publishguy_small.gif'),
                   ]),
    ],
      console=[{'script':'cct.py',
                'icon_resources':[(1, os.path.join('resources','cc.ico'))]
                },
               {'script':'ccl.py',
                'icon_resources':[(1, os.path.join('resources','cc.ico'))]
                },
               ],
      windows=[{'script':'cctag-wiz.py',
                'icon_resources':[(1, os.path.join('resources','cc.ico'))]
               }],
      scripts=['cctag-wiz.py', 'cct.py', 'ccl.py', 'claim.py'],
      packages=['cctag', 'tagger', 'ccrdf',
                'rdflib', 'rdflib.syntax',
                'rdflib.syntax.serializers', 'rdflib.syntax.parsers',
                'rdflib.backends', 'rdflib.model',
                'pyarchive', 'ccwx'],
      options={"py2exe": {"packages": ["encodings", 'rdflib'],
                          "includes": ["dumbdbm"], },
               },
      )

# call the standard distutils builder for the CLI apps (only)
cleanManifest()
setup(name='cct',
      version=CCT_VERSION,
      url='http://creativecommons.org',
      author='Nathan R. Yergler',
      author_email='nathan@yergler.net',
      py_modules=['cct',],
      scripts=['cct.py'],
      packages=['cctag', 'tagger'],
      )

cleanManifest()
setup(name='ccl',
      version=CCT_VERSION,
      url='http://creativecommons.org',
      author='Nathan R. Yergler',
      author_email='nathan@yergler.net',
      py_modules=['ccl',],
      scripts=['ccl.py'],
      packages=['cctag', 'tagger', 'ccrdf', 
                'rdflib', 'rdflib.syntax',
                'rdflib.syntax.serializers', 'rdflib.syntax.parsers',
                'rdflib.backends', 'rdflib.model',],
      )
    
cleanManifest()
setup(name='claim',
      version=CCT_VERSION,
      url='http://creativecommons.org',
      author='Nathan R. Yergler',
      author_email='nathan@yergler.net',
      py_modules=['claim',],
      scripts=['claim.py'],
      packages=['cctag', 'tagger'],
      )

