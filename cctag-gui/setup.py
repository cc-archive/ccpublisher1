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
import platform

from distutils.core import setup
from distutils import sysconfig
from distutils.command import build_scripts, install_data, build_ext
from distutils.errors import CompileError

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

    tmp_dir = './tmp/ccPublisher'
    
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
    libdir = '/usr/local/lib/wxPython-unicode-%s/lib' % wx.__version__
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

# assemble the data files to bundle
pkg_data = [('resources', ['wizard.xrc',
                   os.path.join('resources', 'cc_33.png'),
                   os.path.join('resources', 'cc_33.gif'),
                   os.path.join('resources', 'cc.ico'),
                   os.path.join('resources', 'publishguy_small.gif'),
                   ]),
           ]

# check for win32 support
if sys.platform == 'win32':
    # win32 allows building of executables
    import py2exe

# check for OS X support
if sys.platform == 'darwin':
    import py2app
    pkg_data.append( ('../Frameworks', 
       ['/usr/local/lib/wxPython-unicode-2.5.3.1/lib/libwx_macud-2.5.3.rsrc'])
    )

class build_scripts_cc(build_scripts.build_scripts):
    """Renames scripts on Linux."""

    FILE_MAP = {'cctag-wiz.py' : 'ccpublisher',
                'cct.py'       : 'cct',
                'ccl.py'       : 'ccl',
                'claim.py'     : 'claim',
                }
    
    def run(self):
        build_scripts.build_scripts.run(self)
        
        if platform.system().lower() != 'linux':
            return
        
        for f in os.listdir(self.build_dir):
            fpath=os.path.join(self.build_dir, f)

            if f in self.FILE_MAP:
                new_path = os.path.join(self.build_dir, self.FILE_MAP[f])

                try:
                    os.unlink(new_path)
                except EnvironmentError, e:
                    if e.args[1]=='No such file or directory':
                        pass
                os.rename(fpath, new_path)
                
# call the standard distutils builder for the wizard app
cleanManifest()

setup(name='ccPublisher',
      version=CCT_VERSION,
      description = "Desktop tools for licensing works and uploading to the "
                    "Internet Archive for hosting and cataloging.",
      long_description="",
      url='http://creativecommons.org',
      author='Nathan R. Yergler',
      author_email='nathan@creativecommons.org',
      classifiers= ['Development Status :: 5 - Production/Stable',
                    'Environment :: MacOS X :: Cocoa',
                    'Environment :: Win32 (MS Windows)',
                    'Environment :: X11 Applications :: GTK',
                    'Intended Audience :: End Users/Desktop',
                    'License :: OSI Approved :: GNU General Public License (GPL)',
                    'Natural Language :: English',
                    'Operating System :: OS Independent',
                    'Programming Language :: Python',
                    'Topic :: Multimedia',
                    'Topic :: System :: Archiving',
    ],
      py_modules=['cctag','cct', 'ccl', 'claim', 
                  'html', 'setup', 'wxsupportwiz'],
      data_files=pkg_data,
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
      app = ['cctag-wiz.py'],
      scripts=['cctag-wiz.py', 'cct.py', 'ccl.py', 'claim.py'],
      packages=['cctag', 'tagger', 'ccrdf',
                'rdflib', 'rdflib.syntax',
                'rdflib.syntax.serializers', 'rdflib.syntax.parsers',
                'rdflib.backends', 'rdflib.model',
                'pyarchive', 'ccwx', 'eyeD3'],
      options={"py2exe": {"packages": ["encodings", 'rdflib'],
                          "includes": ["dumbdbm"], },
               "py2app": {"argv_emulation": True,
                          "iconfile": os.path.join('resources', 'cc.icns'),
                          },
               },
      cmdclass={
        'build_scripts': build_scripts_cc,
        },
      )

# see if we need to make the disk image
if 'py2app' in sys.argv:
    # create a disk image
    makeDmg([os.path.join('dist', 'ccPublisher.app')],
             os.path.join('build', 'Publisher.dmg'))
    
