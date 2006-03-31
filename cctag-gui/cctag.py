#!/usr/bin/env python
"""
cctag.py

Provides a wxPython gui for embedding license claims in media files and
generating the cooresponding verification RDF.

Requires wxPython 2.5.1 and Python 2.3.
"""

__id__ = "$Id$"
__version__ = "$Revision$"
__copyright__ = '(c) 2004, Creative Commons, Nathan R. Yergler'
__license__ = 'licensed under the GNU GPL2'

import sys
import os
import pickle

import wx
import wx.xrc as xrc
from wx.xrc import XRCCTRL, XRCID

if sys.platform == 'darwin':
   # fix up the import path so that cctag imports work within the bundle
   sys.path.insert(0, sys.path[-1])

import cctag.rdf as rdf
from cctag.metadata import metadata
from cctag.const import CCT_VERSION

XRC_SOURCE = 'cctag.xrc'
PREFS_FILE = '.cctag.prefs'
LICENSE_URLS = {}

class dropFileTarget(wx.FileDropTarget):
    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self._window = window

    def OnDropFiles(self, x, y, filenames):
        self._window.selectFiles(filenames)
    
class CcTagFrame(wx.Frame):
    def __init__(self, parent):
       self._loadUi(parent)

    def _loadUi(self, parent):
        # create the frame's skeleton
        pre = wx.PreFrame()

        # load the actual definition from the XRC
        res = xrc.XmlResource(XRC_SOURCE)
        res.LoadOnFrame(pre, parent, "MAINFRAME")

        # finish creation
        self.PostCreate(pre)
	self.SetAutoLayout(True)

        # set up drag and drop support
        self.dropTarget = dropFileTarget(self)
        self.SetDropTarget(self.dropTarget)

        # set up the menu bar and status bar
        menubar = res.LoadMenuBar("MAINMENU")
        self.SetMenuBar(menubar)
        self.Fit()

        # bind events to methods
        self._initEvents()
        
        # initialize internals
        self._files = []
        self._readPrefs()
        cmblicense = XRCCTRL(self, "TXT_LICENSE")
        for license in LICENSE_URLS.keys():
           cmblicense.Append(license)

    def _initEvents(self):
        """Initialize event handling."""
        
        self.Bind(wx.EVT_BUTTON, self.onBrowseClick,
                  XRCCTRL(self, "CMD_BROWSE"))

        self.Bind(wx.EVT_BUTTON, self.onEmbed,
                  XRCCTRL(self, "CMD_EMBED"))
        self.Bind(wx.EVT_BUTTON, self.onQuit,
                  XRCCTRL(self, "CMD_CLOSE"))
        
        # hook up the menu dispatch
        self.Bind(wx.EVT_MENU, self.onMenuClick,
                  XRCCTRL(self, "MNU_FILE_QUIT"))

    def onBrowseClick(self, event):
        # user clicked the Browse button; show a file selector
        fileBrowser = wx.FileDialog(self, wildcard="*.*",
                                    style= wx.OPEN|wx.MULTIPLE)
        if fileBrowser.ShowModal() == wx.ID_OK:
            # handle the newly selected file(s)
            self.selectFiles(fileBrowser.GetPaths())

    def selectFiles(self, files):
        self._files = files
        if len(self._files) == 0: return
        
        # set the value of copyright holder (artist) and copyright year
        file_info = metadata(self._files[0])

        try:
           XRCCTRL(self, "TXT_HOLDER").SetValue(str(file_info.getArtist()))
           XRCCTRL(self, "TXT_YEAR").SetValue(str(file_info.getYear()))
        except NotImplementedError:
           # not a supported file type; show an error message
           wx.MessageBox("Unknown file type; unable to embed license.",
                         caption="ccTag: Error.",
                         style=wx.OK|wx.ICON_ERROR, parent=self)
           return
        
        # should we check for an existing claim here and parse if available?
        
        # set the value of the filenames control
        XRCCTRL(self, "TXT_FILENAME").SetValue(", ".join(self._files))

        # clear the verification RDF
        XRCCTRL(self, "TXT_VERIFICATION").SetValue("")
        
    def onMenuClick(self, event):
        # dispatch menu events to the proper handler

        id = event.GetId()

        # XXX: 5006 seems to be magic on my OS X system; is it always?
        if id == XRCID("MNU_FILE_QUIT") or id == 5006:
            self.onQuit(event)
        elif id == XRCID("wxID_ABOUT"):
            self.onAbout(event)
        else:
            print "Unknown menu event:", event.GetId()

    def onEmbed(self, event):
        # make sure we have all the information we need
        if not(self._readyToEmbed(event)):
            return

        # get form values
        license = XRCCTRL(self, "TXT_LICENSE").GetValue()
        verify_url = XRCCTRL(self, "TXT_VERIFICATION").GetValue()
        year = XRCCTRL(self, "TXT_YEAR").GetValue()
        holder = XRCCTRL(self, "TXT_HOLDER").GetValue()

        for filename in self._files:
            metadata(filename).embed(license, verify_url, year, holder)

        # make sure we have the license RDF for this license
        if license not in LICENSE_URLS or \
               (license in LICENSE_URLS and LICENSE_URLS[license] is None):
            LICENSE_URLS[license] = rdf.getLicense(license)
        
        # generate the verification RDF
        verification = rdf.generate(self._files, verify_url, 
                                    license, year, holder,
                                    license_rdf=LICENSE_URLS[license])
        XRCCTRL(self, "TXT_RDF").SetValue(verification)
    
    def onQuit(self, event):
        # destroy the top level window (self) to trigger quitting the app
        self._writePrefs()
        self.Destroy()

    def onAbout(self, evt):
        str = """\
ccTag %s

(c) 2004, Creative Commons,
Nathan R. Yergler <nathan@yergler.net>
http://creativecommons.org
""" % CCT_VERSION
        dlg = wx.MessageDialog(self, str, 'About ccTag', wx.OK | wx.CENTRE)
        dlg.ShowModal()
        dlg.Destroy()

    def _readyToEmbed(self, event):
        """Verifies the user has supplied the necessary input and presents
        any error messages necessary; returns True if all fields are
        populated, False if any are missing.
        """

        # make sure file(s) have been selected
        if len(self._files) == 0:
            wx.LogError("You must select a file before you can embed license information.")
            return False

        if len(XRCCTRL(self, "TXT_LICENSE").GetValue().strip()) == 0:
            wx.LogError("You must specify a license URL.")
            return False
            
        if len(XRCCTRL(self, "TXT_VERIFICATION").GetValue().strip()) == 0:
            wx.LogError("You must specify a verification URL.")
            return False

        return True

    def _readPrefs(self):
       global LICENSE_URLS

       if os.path.exists(PREFS_FILE):
          try:
              LICENSE_URLS = pickle.load(file(PREFS_FILE))
          except:
              LICENSE_URLS = {}

    def _writePrefs(self):
        pickle.dump(LICENSE_URLS, file(PREFS_FILE, 'w'))

class CcTagWizard(CcTagFrame):
   def _loadUi(self, parent):
      pass
   
class CCTagApp(wx.App):
   def OnInit(self):
      # perform wx intialization
      wx.InitAllImageHandlers()

      # take care of any custom settings here
      self.SetAppName('ccTag')

      # create the main window and set it as the top level window
      self.main = CcTagFrame(None)
      self.main.Show(True)

      self.SetTopWindow(self.main)
      return True

   def MacOpenFile(self, filename):
      # pass the filename into the main form
      if self.main:
         self.main.selectFiles([filename])
        
def main(argv=[]):
   # create the application and execute it
   app = CCTagApp(0, useBestVisual=False)

   if len(argv) > 1:
     app.main.selectFiles(argv[1:])

   app.MainLoop()
    
if __name__ == '__main__':

    # set any platform-specific parameters
    if sys.platform == 'darwin':
        # set the file path to the XRC resource file
        # to handle the app bundle properly
        XRC_SOURCE = os.path.join(os.path.dirname(sys.argv[0]), XRC_SOURCE)
        PREFS_FILE = os.path.join(os.path.dirname(sys.argv[0]), PREFS_FILE)
    elif sys.platform == 'win32':
        XRC_SOURCE = os.path.join(os.path.dirname(sys.argv[0]),
                                  'resources', XRC_SOURCE)
        PREFS_FILE = os.path.join(os.path.dirname(sys.argv[0]),
                                  'resources', PREFS_FILE)
    
    main(sys.argv)
    
