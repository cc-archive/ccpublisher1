#!/usr/bin/env python
"""
cctag-wiz.py

Provides a wizard for embedding license claims in media files and
generating the corresponding verification RDF.

Requires wxPython 2.5.2 and Python 2.3.
"""

__id__ = "$Id$"
__version__ = "$Revision$"
__copyright__ = '(c) 2004, Creative Commons, Nathan R. Yergler'
__license__ = 'licensed under the GNU GPL2'

import sys
import os
import pickle
import webbrowser
import ftplib
import shelve
import socket

import wx
import wx.xrc as xrc
from wx.xrc import XRCCTRL, XRCID

import ccwx.stext
import ccwx.xrcwiz
from ccwx.xrcwiz import XrcWizPage
from ccwx.wizpages import DestWizPage, ProgressWizPage, FileFormatWizPage
from ccwx.wizpages import ChooserWizPage, FilesWizPage, LoginWizPage

import cctag.rdf as rdf
from cctag.metadata import metadata
from cctag.const import CCT_VERSION

import pyarchive
import html

XRC_SOURCE = 'wizard.xrc'
PREFS_FILE = '.publisher.prefs'
IMAGES_DIR = 'resources'
ICON_FILE = 'cc.ico'
ERR_LOG = 'err.log'

LICENSE_URLS = {}

class dropFileTarget(wx.FileDropTarget):
    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self._window = window

    def OnDropFiles(self, x, y, filenames):
        self._window.selectFiles(filenames)

class CcTagWizard(ccwx.xrcwiz.XrcWiz):
   def __init__(self, app):
      ccwx.xrcwiz.XrcWiz.__init__(self, app, 
				  filename=XRC_SOURCE, id='FRM_MAIN') 

      _icon = wx.Icon(ICON_FILE, wx.BITMAP_TYPE_ICO)
      self.SetIcon(_icon)

      self._files = []
      self.__images = wx.ImageList(33,33)
      self.uploadingToArchive = True
      
      # load the wizard pages from XRC
      self.pages.append(XrcWizPage(self, self.xrc, 'CCTAG_WELCOME',
                                   'Welcome to Publisher'))
      self.pages.append(FilesWizPage(self, self.xrc, 'DROPFILES',
                                     'Select Your File'))
      self.pages.append(XrcWizPage(self, self.xrc, 'WORK_METADATA',
                                   'Tell Us About Your File'))
      self.pages.append(ChooserWizPage(self))
      self.pages.append(LoginWizPage(self, self.xrc, 'ARCHIVE_LOGIN'))
      self.pages.append(XrcWizPage(self, self.xrc, 'WORK_TYPE',
                        'Select Your Archive Collection'))
      self.pages.append(FileFormatWizPage(self, self.xrc, 'FILE_FORMAT'))
      self.pages.append(XrcWizPage(self, self.xrc, 'READY',
                                   'Tag and Send Your File to the Web'))
      self.pages.append(XrcWizPage(self, self.xrc, 'ARCHIVE_METADATA',
                                   'Tell Us More About your File'))
      self.pages.append(ProgressWizPage(self, self.xrc, 'FTP_PROGRESS',
                                        'Uploading to the Internet Archive'))

      # set the initial page ordering
      self.chainPages()

      # add the additional pages for self-hosting support
      selfhost_start = len(self.pages)

      self.pages.append(XrcWizPage(self, self.xrc, 'VERIFICATION',
                                   'Where Will Your Host Your File?'))
      self.pages.append(self.getPage('READY'))
      self.pages.append(XrcWizPage(self, self.xrc, 'VRDF',
                                   'Get Code For Your Web Page'))

      self.chainPages(start=selfhost_start)
      self.cur_page = 0
      self.addCurrent(None)

      self.pages[self.cur_page].Show()

      # connect event handlers
      self.Bind(wx.EVT_BUTTON, self.onHelp, XRCCTRL(self, "HELP_WHAT_IS_IA"))
      self.Bind(wx.EVT_BUTTON, self.onHelp, XRCCTRL(self, "HELP_NO_IA_ACCOUNT"))
      self.Bind(wx.EVT_BUTTON, self.onHelp, XRCCTRL(self, "HELP_WHAT_TYPES"))
      self.Bind(wx.EVT_BUTTON, self.onHelp, XRCCTRL(self, "HELP_EMBEDDING"))

      self.Bind(wx.EVT_BUTTON, self.onShowAdvWork,
                XRCCTRL(self, "CMD_ADV_WORKMETA"))
      self.Bind(wx.EVT_BUTTON, self.onSelfHost,
                XRCCTRL(self, "CMD_HOST_MYSELF"))
      self.Bind(wx.EVT_BUTTON, self.saveRdf, XRCCTRL(self, "CMD_SAVE_RDF"))

      # XXX: why the hell are these lines needed?
      self.Bind(wx.EVT_BUTTON, self.onNext, XRCCTRL(self, "CMD_NEXT"))
      self.Bind(wx.EVT_BUTTON, self.onPrev, XRCCTRL(self, "CMD_PREV"))

      # set up drag and drop support
      self.SetDropTarget(dropFileTarget(self))

      # explicitly attach the drop target to the listview (OSX)
      XRCCTRL(self, "LST_FILES").SetDropTarget(dropFileTarget(self)) 

      self.SetAutoLayout(True)
      self.__platformLayout()
      self._initImages()
      self.Layout()

   def __platformLayout(self):
       self.SetSize(self.GetMinSize())

       # check the background color
       if sys.platform != 'darwin':
           html.BGCOLOR = "%X" % \
                     wx.SystemSettings_GetColour(wx.SYS_COLOUR_BTNFACE).GetRGB()

   def onShowAdvWork(self, event):
       XRCCTRL(self, "PNL_ADVANCED").Show(
           not(XRCCTRL(self, "PNL_ADVANCED").IsShown()))

   def onSelfHost(self, event):
       """User chose to self-host; reset the next page and
       fire a "next" event to show verification url entry.
       """

       self.uploadingToArchive = False

       self.pages[self.cur_page].SetNext(self.getPage('VERIFICATION'))
       self.pages[self.cur_page].GetNext().SetPrev(self.pages[self.cur_page])
       
       self.onNext(None)
        
   def OnPageChanging(self, event):
       # call the super class
       if not(event.GetPage().validate(event)):
           event.Veto()
           return

       # additional dispatch
       if event.GetPage().xrcid == 'ARCHIVE_LOGIN' and \
          self.uploadingToArchive and \
          event.direction:
           # see if the user selected a work format;
           # if so, set the appropriate value on the
           # work format page and skip it.

           if XRCCTRL(self, "CMB_WORK_FORMAT").GetValue() == 'Audio':
               XRCCTRL(self, "RDB_AUDIO").SetValue(True)

               # store the current next page
               if not(hasattr(event.GetPage(), 'initialNext')):
                   event.GetPage().initialNext = event.GetPage().GetNext()

               event.GetPage().SetNext(self.getPage('WORK_TYPE').GetNext())
               event.GetPage().GetNext().SetPrev(event.GetPage())

           elif XRCCTRL(self, "CMB_WORK_FORMAT").GetValue() == 'Video':
               XRCCTRL(self, "RDB_VIDEO").SetValue(True)

               # store the current next page
               if not(hasattr(event.GetPage(), 'initialNext')):
                   event.GetPage().initialNext = event.GetPage().GetNext()

               event.GetPage().SetNext(self.getPage('WORK_TYPE').GetNext())
               event.GetPage().GetNext().SetPrev(event.GetPage())

           else:
               # see if the user went back and forth, and if so, reset the
               # next/prev pages if necessary
               if hasattr(event.GetPage(), 'initialNext'):
                   event.GetPage().SetNext(event.GetPage().initialNext)
                   event.GetPage().GetNext().SetPrev(event.GetPage())

       if event.GetPage().xrcid == 'ARCHIVE_LOGIN' and \
          self.uploadingToArchive and event.direction:

           if XRCCTRL(self, "TXT_USERNAME").GetValue().strip() == '' or \
              XRCCTRL(self, "TXT_PASSWORD").GetValue().strip() == '':
               wx.MessageBox("Please enter your archive.org username and password.",
                         caption="publisher: Error.",
                         style=wx.OK|wx.ICON_ERROR, parent=self)
               event.Veto()

       if event.GetPage().xrcid == 'FILE_FORMAT' and \
          event.direction:
           if not (event.GetPage().allFormatted()):
               wx.MessageBox("Please select a format for each file.",
                         caption="publisher: Error.",
                         style=wx.OK|wx.ICON_ERROR, parent=self)
               event.Veto()
               
       if event.GetPage().xrcid == 'READY' and \
              not(self.uploadingToArchive) and \
              event.direction:
           __cur_cursor = self.GetCursor()
           wx.Yield()
           self.SetCursor(wx.StockCursor(wx.CURSOR_WAIT))
           
           self.embed(event)
           wx.Yield()

           self.SetCursor(__cur_cursor)

       if event.GetPage().xrcid == 'READY' and \
          self.uploadingToArchive and \
          event.direction:

           if XRCCTRL(self, "CHK_ADV_ARCHIVE").GetValue():
               event.GetPage().SetNext(self.getPage('ARCHIVE_METADATA'))
           else:
               event.GetPage().SetNext(self.getPage('FTP_PROGRESS'))

           event.GetPage().GetNext().SetPrev(event.GetPage())
               
       if event.GetPage().xrcid == 'CHOOSE_LICENSE' and event.direction:
           self.__license_url = event.GetPage().getLicenseUrl()
           self.__license_name = event.GetPage().getLicenseName()
           if self.__license_url is None:
               # no license was issued; veto
               wx.MessageBox("You must select a license.",
                         caption="publisher: Error.",
                         style=wx.OK|wx.ICON_ERROR, parent=self)
               event.Veto()

       if event.GetPage().xrcid == 'VERIFICATION' and \
          XRCCTRL(self, "TXT_VERIFICATION").GetValue().strip() == '' and \
          event.direction:
           wx.MessageBox("Please enter the verification URL.",
                         caption="publisher: Error.",
                         style=wx.OK|wx.ICON_ERROR, parent=self)
           event.Veto()

       if event.GetPage().GetNext() == self.getPage('READY'):
           # set Ready's previous page appropriately
           event.GetPage().GetNext().SetPrev(event.GetPage())

   def OnPageChanged(self, event):
       if event.GetPage().xrcid == 'FILE_FORMAT':
           # see if we know the format for all files
           if event.GetPage().allFormatted():
               if event.direction:
                   self.onNext(None)
               else:
                   self.onPrev(None)
           
       if event.GetPage().xrcid == 'FTP_PROGRESS':
           # store the current cursor and set to "wait"
           __cur_cursor = self.GetCursor()
           self.SetCursor(wx.StockCursor(wx.CURSOR_WAIT))
           
           # disable the finish button
           XRCCTRL(self, "CMD_NEXT").Disable()

           # upload to the archive
           try:
               url = self.archive(event)

               # display final information
               event.GetPage().setUrl(url)
           except ftplib.error_perm, e:
               # invalid username and password
               wx.MessageBox("Error logging into the Internet Archive;\n"
                             "invalid username or password.",
                         caption="publisher: Error.",
                         style=wx.OK|wx.ICON_ERROR, parent=self)
               self.setPage('ARCHIVE_LOGIN')
           except pyarchive.exceptions.SubmissionError, e:
               wx.MessageBox("An error occurred while submitting your file;\n"
                             "%s: %s" % e.args,
                             caption="publisher: Error.",
                             style=wx.OK|wx.ICON_ERROR, parent=self)

               return
           except socket.error, e:
               retry = \
                  wx.MessageBox("An error occurred while uploading your file. "
                             "The connection may have timed out or "
                             "disconnected.\n"
                             "Would you like to retry?",
                             caption="publisher: Error.",
                             style=wx.YES_NO|wx.ICON_ERROR, parent=self)
               if retry == wx.ID_YES:
                   self.OnPageChanged(event)

               return

           # reset the cursor
           self.SetCursor(__cur_cursor)
           
           XRCCTRL(self, "CMD_NEXT").Enable()

       if event.GetPage().xrcid == 'WORK_METADATA':
           # check if the holder is pre-populated and select the first item
           # if it is.
           if XRCCTRL(self, "TXT_HOLDER").GetCount() > 0:
               XRCCTRL(self, "TXT_HOLDER").SetSelection(0)

           # see if we can preset the work format
           if self.getPage('FILE_FORMAT').allFormatted() or \
                  ('ogg' in [os.path.split(n)[-1].split('.')[-1]
                             for n in self._files]):
               XRCCTRL(self, "CMB_WORK_FORMAT").SetValue('Audio')
           else:
               # assume video
               XRCCTRL(self, "CMB_WORK_FORMAT").SetValue('Video')
           
       if event.GetPage().xrcid == 'VRDF':
           XRCCTRL(self, "LBL_VRDF_DEST").SetLabel(
               "Copy and paste the text below into the document at %s" %
               XRCCTRL(self, "TXT_VERIFICATION").GetValue()
               )

       if event.GetPage().xrcid == 'READY':
           # set up the summary window
           XRCCTRL(self, "LST_READY_FILES").Clear()
           XRCCTRL(self, "LST_READY_FILES").AppendItems(self._files)

           ready_msg = "Publisher has collected all the information " \
           "neccessary to license your files with the %s license." % (
               self.__license_name)
           
           if self.uploadingToArchive:
               ready_msg = "%s\n%s" % (ready_msg, 
                   "Your files will be uploaded to the Internet Archive."
                   )
               XRCCTRL(self, "CHK_ADV_ARCHIVE").Show()
           else:
               ready_msg = "%s\n%s" % (ready_msg, 
                   "Publisher will generate HTML code which you should "
                   "copy into the code of your web page."
                   )
               XRCCTRL(self, "CHK_ADV_ARCHIVE").Hide()

           XRCCTRL(self, "LBL_READY_MSG").SetLabel(ready_msg)

       self.Layout()
               
   def _initImages(self):
       """Loads the image list with the necessary objects"""
       self.__images.Add(wx.Bitmap(os.path.join(IMAGES_DIR, "cc_33.png")))

       XRCCTRL(self, "LST_FILES").SetImageList(self.__images,
                                               wx.IMAGE_LIST_NORMAL)
       
   def onHelp(self, event):
       if event.GetId() == XRCID('HELP_WHAT_IS_IA'):
           webbrowser.open('http://www.archive.org/about/about.php',
                           True, True)
       elif event.GetId() == XRCID('HELP_NO_IA_ACCOUNT'):
           webbrowser.open('http://www.archive.org/account/login.createaccount.php',
                           True, True)
       elif event.GetId() == XRCID('HELP_WHAT_TYPES'):
           if sys.platform == 'darwin':
               img_path = '.'
           else:
               img_path = 'resources'
               
           help = html.HtmlHelp(self, 'Creative Commons Publisher',
                                html.MORE_INFO % (CCT_VERSION, img_path))
           help.Show()
       elif event.GetId() == XRCID('HELP_EMBEDDING'):
           webbrowser.open('http://creativecommons.org/technology/embedding')

   def deleteFiles(self, shortnames):
        
        items = [n for n in self._files if n.split(os.sep)[-1] in shortnames]

        for item in items:
             del self._files[self._files.index(item)]
             
        self.resetFileList()
        
   def selectFiles(self, files):
        for fn in files:
           # set the value of copyright holder (artist) and copyright year
           file_info = metadata(fn)

           try:
               artist = str(file_info.getArtist())
               if artist:
                   XRCCTRL(self, "TXT_HOLDER").Append(artist)
               XRCCTRL(self, "TXT_YEAR").SetValue(str(file_info.getYear()))
               XRCCTRL(self, "TXT_WORK_TITLE").SetValue(
                   str(file_info.getTitle()))
           except NotImplementedError:
              # not a supported file type; show an error message
              #wx.MessageBox("Unknown file type; unable to embed license.",
              #              caption="publisher: Error.",
              #              style=wx.OK|wx.ICON_ERROR, parent=self)
              pass
          
           self._files.append(fn)
        
        #XXX should we check for an existing claim here and parse if available?

        # reset the file display
        self.resetFileList()
        self.getPage('FILE_FORMAT').setFiles(self._files)
        
        # clear the verification RDF
        XRCCTRL(self, "TXT_VERIFICATION").SetValue("http://")
        XRCCTRL(self, "TXT_RDF").SetValue("")

   def resetFileList(self):
        # reset the file view
        XRCCTRL(self, "LST_FILES").ClearAll()
        
        for fn in self._files:
           XRCCTRL(self, "LST_FILES").\
                         InsertImageStringItem(0, fn.split(os.sep)[-1], 0)

   def __workMetadata(self, filename=None):
       meta = {}

       formats = {'Other':None,
                  'Audio':'Sound',
                  'Video':'MovingImage',
                  'Image':'StillImage',
                  'Text':'Text',
                  'Interactive':'InteractiveResource'
                  }
       
       controls = {'TXT_WORK_TITLE':'title',
                   'TXT_DESCRIPTION':'description',
                   'TXT_CREATOR':'creator',
                   'TXT_SOURCE_URL':'source',
                   'TXT_KEYWORDS':'subjects'
                   }

       # get the text control values
       for c in controls:
           if XRCCTRL(self, c).GetValue():
               meta[controls[c]] = XRCCTRL(self, c).GetValue()

       # get the work format
       meta['format'] = formats[XRCCTRL(self, "CMB_WORK_FORMAT").GetValue()]
       
       if filename is None:
           return meta

       try:
            if 'creator' not in meta:
                meta['creator'] = metadata(filename).getArtist()

            if 'title' not in meta:
                meta['title'] = metadata(filename).getTitle()
       except NotImplementedError, e:
            pass
       
       return meta
               
   def embed (self, event):
        # make sure we have all the information we need
        #if not(self._readyToEmbed(event)):
        #    return

        # get form values
        license = self.__license_url #XRCCTRL(self, "TXT_LICENSE").GetValue()
        verify_url = XRCCTRL(self, "TXT_VERIFICATION").GetValue()
        year = XRCCTRL(self, "TXT_YEAR").GetValue()
        holder = XRCCTRL(self, "TXT_HOLDER").GetValue()

        for filename in self._files:
            try:
                 metadata(filename).embed(license, verify_url, year, holder)
            except NotImplementedError, e:
                 pass

        # generate the verification RDF
        verification = rdf.generate(self._files, verify_url, 
                                    license, year, holder,
                                    work_meta=self.__workMetadata())

        XRCCTRL(self, "TXT_RDF").SetValue(verification)

   def __archiveId(self, workMeta):
       """Generates an archive.org identifier from work metadata or
       embedded ID3 tags."""

       id_pieces = []
       if 'creator' in workMeta:
           id_pieces.append(workMeta['creator'])

       if 'title' in workMeta:
           id_pieces.append(workMeta['title'])

       if len(id_pieces) < 2:
           id_pieces = id_pieces + [os.path.split(n)[1] for n in self._files]
           
       archive_id = pyarchive.identifier.munge(" ".join(id_pieces))
       id_avail = pyarchive.identifier.available(archive_id)

       # if the id is not available, add a number to the end
       # and check again
       i = 0
       orig_id = archive_id
       while not(id_avail):
           archive_id = '%s_%s' % (orig_id, i)
           
           i = i + 1
           id_avail = pyarchive.identifier.available(archive_id)

       return archive_id
           
   def archive(self, event):
       """Embed the license and upload files to archive.org"""

       # generate the identifier and make sure it's available
       workMeta = self.__workMetadata(self._files[0])
       archive_id = self.__archiveId(workMeta)

       # determine the appropriate collection
       if XRCCTRL(self, "RDB_AUDIO").GetValue():
           archive_collection = pyarchive.const.OPENSOURCE_AUDIO
           submission_type = pyarchive.const.AUDIO
       else:
           archive_collection = pyarchive.const.OPENSOURCE_MOVIES
           submission_type = pyarchive.const.VIDEO
           
       # generate the verification url
       v_url = pyarchive.identifier.verify_url(archive_collection, archive_id)
       
       # embed the license in the file(s)
       # get form values
       license = self.__license_url
       year = XRCCTRL(self, "TXT_YEAR").GetValue()
       holder = XRCCTRL(self, "TXT_HOLDER").GetValue()

       for filename in self._files:
           try:
                metadata(filename).embed(license, v_url, year, holder)
           except NotImplementedError, e:
                pass

       # create the submission object
       submission = pyarchive.submission.ArchiveItem(
           archive_id, archive_collection,
           submission_type,
           (('title' in workMeta and workMeta['title']) or 'untitled')
           )

       # assign any work metadata to the submission for carry over
       for key in workMeta:
           submission[key] = workMeta[key]

       # assemble the submission metadata
       archive_meta_controls = {'TXT_TAPER':pyarchive.const.TAPER,
                                'TXT_SOURCE':pyarchive.const.SOURCE,
                                'TXT_RUNTIME':pyarchive.const.RUNTIME,
                                'TXT_DATE':pyarchive.const.DATE,
                                'TXT_NOTES':pyarchive.const.NOTES,
                                }
       
       submission['licenseurl'] = license
       for key in archive_meta_controls:
           if XRCCTRL(self, key).GetValue():
               submission[archive_meta_controls[key]] = \
                          XRCCTRL(self, key).GetValue()
               
       for filename in self._files:
           sub = submission.addFile(filename, pyarchive.const.ORIGINAL,
                              claim = self.__claimString(license, v_url, year, holder)
                              )
           sub.format = self.getPage('FILE_FORMAT').getFormat(filename)

       submission.submit(XRCCTRL(self, "TXT_USERNAME").GetValue(),
                         XRCCTRL(self, "TXT_PASSWORD").GetValue(),
                         callback=XRCCTRL(self, "FTP_PROGRESS").callback)

       return v_url

   def __claimString(self, license, verification, year, holder):
       return "%s %s. Licensed to the public under %s verify at %s" % (
            year, holder, license, verification )
       
   def saveRdf(self, event):
       fileBrowser = wx.FileDialog(self, wildcard="*.txt",
                                   style= wx.SAVE)
       if fileBrowser.ShowModal() == wx.ID_OK:
           # save the RDF into the selected filename
           outfile = file(fileBrowser.GetPath(), 'w')
           outfile.write(XRCCTRL(self, "TXT_RDF").GetValue())
           outfile.close()
   
class CcWizApp(wx.App):
   def OnInit(self):
      # read preferences, if any
      self.__readPrefs()
      
      wx.InitAllImageHandlers()

      # take care of any custom settings here
      self.SetAppName('Publisher')

      # create the main window and set it as the top level window
      self.main = CcTagWizard(self)
      self.main.Show(True)

      self.SetTopWindow(self.main)

      return True

   def OnExit(self):
       # write out preferences
       self.__writePrefs()

   def __readPrefs(self):
       self.prefs = shelve.open(PREFS_FILE)
       
   def __writePrefs(self):
       self.prefs.close()
   
   def MacOpenFile(self, filename):
      # pass the filename into the main form
      if self.main:
         self.main.selectFiles([filename])
        
def main(argv=[]):
   # create the application and execute it
   import wxsupportwiz
   wxsupportwiz.wxAddExceptHook('http://api.creativecommons.org/traceback.py',
                                CCT_VERSION)
   app = CcWizApp(filename=ERR_LOG)

   if len(argv) > 1:
       app.main.selectFiles(argv[1:])

   app.MainLoop()
   
if __name__ == '__main__':

    # set any platform-specific parameters
    if sys.platform == 'darwin':
        # set the file path to the XRC resource file
        # to handle the app bundle properly
        XRC_SOURCE = os.path.join(os.path.dirname(sys.argv[0]), XRC_SOURCE)
        IMAGES_DIR = os.path.dirname(sys.argv[0])

        # store the preferences and error log in ~/Library/Application Support/ccPublisher
        app_lib_dir = os.path.expanduser('~/Library/Application Support/ccPublisher')
        if not(os.path.exists(app_lib_dir)):
               os.makedirs(app_lib_dir)
        PREFS_FILE = os.path.join(app_lib_dir, PREFS_FILE)
        ERR_LOG = os.path.join(app_lib_dir, ERR_LOG)
        
    elif sys.platform == 'win32':
        IMAGES_DIR = os.path.join(os.path.dirname(sys.argv[0]), IMAGES_DIR)

        XRC_SOURCE = os.path.join(os.path.dirname(sys.argv[0]),
                                  'resources', XRC_SOURCE)
        ICON_FILE = os.path.join(os.path.dirname(sys.argv[0]),
                                  'resources', ICON_FILE)
        PREFS_FILE = os.path.join(os.path.dirname(sys.argv[0]),
                                  PREFS_FILE)
    
    cmdArgs = sys.argv

    main(cmdArgs)

