__id__ = "$Id$"
__version__ = "$Revision$"
__copyright__ = '(c) 2004, Creative Commons, Nathan R. Yergler'
__license__ = 'licensed under the GNU GPL2'

import wx
import wx.wizard
import wx.grid
import wx.lib.dialogs

import urllib2
import libxml2
import libxslt
import os
import sys

import pyarchive.const
import pyarchive.utils

from wx.xrc import XRCCTRL, XRCID

import xrcwiz
import stext
import html
            
class FileFormatWizPage(xrcwiz.XrcWizPage):
    def __init__(self, parent, xrc, xrcid):
        xrcwiz.XrcWizPage.__init__(self, parent, xrc, xrcid,
                                   'Add Format Information')

        self.files = {}
        self.formats = {}
        self.filenames = []

        self.panel = XRCCTRL(self, "PNL_FILELIST")

    def __detachAll(self):
        for filename in self.files.keys():
            self.panel.GetSizer().Detach(self.files[filename][0])
            self.panel.GetSizer().Detach(self.files[filename][1])

        self.files = {}
        self.filenames = []
        
    def setFiles(self, files):
        self.__detachAll()

        self.filenames = files

        for fn in self.filenames:
            # add the label
            label = wx.StaticText(self.panel,
                                  label = os.path.split(fn)[1])
            self.panel.GetSizer().Add(label, flag=wx.EXPAND)

            # add the combo box
            cmb = wx.ComboBox(self.panel,
                         style=wx.CB_DROPDOWN|wx.CB_READONLY,
                         choices = pyarchive.const.VALID_FORMATS
                         )
            cmb._filename = fn
            self.panel.GetSizer().Add(cmb, flag=wx.EXPAND)

            self.files[fn] = (label, cmb)
            self.formats[fn] = None
            
            # bind to the change event
            self.Bind(wx.EVT_COMBOBOX, self.onChooseFormat, cmb)

        # try to detect file formats
        self.__detect()
        
        self.Layout()

    def __detect(self):
        # attempt to detect the file type for each file
        for fn in self.filenames:
            # see if the user has already set a format for this file
            if self.formats[fn] is not None:
                continue
            
            # attempt to detect the fileformat
            fileinfo = pyarchive.utils.getFileInfo(os.path.split(fn)[1], fn)

            if fileinfo[2]:
                if fileinfo[2][1]:
                    # non-vbr
                    try:
                        self.formats[fn] = pyarchive.const.MP3[fileinfo[2][0]]
                    except KeyError, e:
                        # not a known bit rate; probably VBR
                        self.formats[fn] = pyarchive.const.MP3_VBR
                        
                else:
                    self.formats[fn] = pyarchive.const.MP3_VBR

                # set the combo box value
                self.files[fn][1].SetValue(self.formats[fn])
    
    def onChooseFormat(self, event):
        # find the appropriate file
        self.formats[self.FindWindowById(event.GetId())._filename] = self.FindWindowById(event.GetId()).GetValue()

    def allFormatted(self):
        """Return True if all files have a format assigned."""
        for k in self.formats:
            if self.formats[k] is None:
                return False

        return True

    def getFormat(self, filename):
        return self.formats[filename]
        
class FilesWizPage(xrcwiz.XrcWizPage):
    def __init__(self, parent, xrc, xrcid, headline):
        xrcwiz.XrcWizPage.__init__(self, parent, xrc, xrcid, headline)

        if isinstance(xrc, str):
            res = wx.xrc.XmlResource(xrcfile)
        elif isinstance(xrc, wx.xrc.XmlResource):
            res = xrc

        # load the pop up menu and attach
        self.__ctx_menu = res.LoadMenu("MNU_FL_POPUP")

        # bind event handlers
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.onRightClick,
                  XRCCTRL(self, "LST_FILES"))
        self.Bind(wx.EVT_MENU, self.__menuDispatch,
                  XRCCTRL(self, "MNU_FL_DELETE"))
        self.Bind(wx.EVT_MENU, self.__menuDispatch,
                  XRCCTRL(self, "MNU_FL_BROWSE"))
        self.Bind(wx.EVT_BUTTON, self.onBrowse,
                  XRCCTRL(self, "CMD_BROWSE"))
        self.Bind(wx.EVT_BUTTON, self.onDeleteItem,
                  XRCCTRL(self, "CMD_DELETE"))

        
        self.Fit()

    def onRightClick(self, event):
        XRCCTRL(self, "LST_FILES").Select(event.GetIndex())
        self.PopupMenu(self.__ctx_menu, event.GetPosition())

    def __menuDispatch(self, event):
        if event.GetId() == XRCID("MNU_FL_BROWSE"):
            self.onBrowse(event)
        elif event.GetId() == XRCID("MNU_FL_DELETE"):
            self.onDeleteItem(event)
            
    def onDeleteItem(self, event):
        items = []

        selected = XRCCTRL(self, "LST_FILES").GetFirstSelected()

        while selected >= 0:
            items.append(XRCCTRL(self, "LST_FILES").GetItemText(selected))
            selected = XRCCTRL(self, "LST_FILES").GetNextSelected(selected)

        self.parent.deleteFiles(items)

    def onBrowse(self, event):
        # user clicked the Browse button; show a file selector
        fileBrowser = wx.FileDialog(self, wildcard="*.*",
                                    style= wx.OPEN|wx.MULTIPLE)

        # reset the default directory
        if sys.platform == 'win32':
            # Desktop
            fileBrowser.SetPath(os.environ['USERPROFILE'] +
                                os.path.sep + 'Desktop')
            
        if fileBrowser.ShowModal() == wx.ID_OK:
            # handle the newly selected file(s)
            self.parent.selectFiles(fileBrowser.GetPaths())

    def validate(self, event):
       if event.direction:
           if len(self.parent._files) == 0:
               # user must select at least one file
               wx.MessageBox("You must select at least one file to license.",
                         caption="ccTag: Error.",
                         style=wx.OK|wx.ICON_ERROR, parent=self)
               event.Veto()
               return False

       return True

class ProgressCallback:
    def __init__(self, progress_page):
        self.pp = progress_page
        self.__delta = 1
            
    def reset(self, filename=None, steps=None):
        self.__filename = filename
        self.__steps = steps
        self.__bytes = 0
        
        if self.__filename is not None:
            # find the size of the file and set the total number of bytes
            self.__size = os.path.getsize(filename)
            XRCCTRL(self.pp, "WXG_PROGRESS").SetRange(self.__size)
        else:
            self.__size = 1
            XRCCTRL(self.pp, "WXG_PROGRESS").SetRange(steps)

        XRCCTRL(self.pp, "WXG_PROGRESS").SetValue(0)
        
    def increment(self, bytes=None, status=None):
        if bytes is None:
            bytes = self.__delta
        else:
            self.__bytes += bytes
            
        XRCCTRL(self.pp, "WXG_PROGRESS").SetValue(
            XRCCTRL(self.pp, "WXG_PROGRESS").GetValue() + bytes)
        wx.Yield()

        if status is not None:
            self.status(status)
        else:
            self.status('uploading %s (%s %%)...' % (self.__filename,
                             (self.__bytes * 100 / self.__size) )
                        )

    __call__ = increment

    def finish(self):
        self.status('done.')
        XRCCTRL(self.pp, "WXG_PROGRESS").SetValue(
            XRCCTRL(self.pp, "WXG_PROGRESS").GetRange()
            )
        
    def status(self, status):
        XRCCTRL(self.pp, "LBL_CURRENTLY").SetLabel(status)
        wx.Yield()
    
class ProgressWizPage(xrcwiz.XrcWizPage):
    HTML_FINISHED = """<html><body bgcolor="#%s"><p>Your file has been sent
    to the Internet Archive for free hosting.  After it's approved by the
    Archive curator (usually within 24 hours), you will be able to download
    your file from the URL:<br>
    <a href="%s">%s</a>.</p>
    <p>Your file is also ready to be file-shared; just drop it in your
    shared folder.</p>
    </body></html>"""
    
    def __init__(self, parent, xrc, xrcid, headline):
        xrcwiz.XrcWizPage.__init__(self, parent, xrc, xrcid, headline)

        self.callback = ProgressCallback(self)

        self.html = html.WebbrowserHtml(self, -1)
        self.setUrl('foo', False)

        ir = self.html.GetInternalRepresentation()
        self.html.SetSize( (ir.GetWidth()+25, ir.GetHeight()+25) )

        self.GetSizer().Add(self.html, (4,0), (1,1), flag=wx.EXPAND)
        
        self.Layout()

    def setUrl(self, url, show=True):
        self.html.SetPage(self.HTML_FINISHED % (html.BGCOLOR, url, "<br>".join(url.split('?')) ) )
        self.html.Show(show)

class LoginWizPage(xrcwiz.XrcWizPage):
    def __init__(self, parent, xrc, xrcid):
        xrcwiz.XrcWizPage.__init__(self, parent, xrc, xrcid,
                                   "Login to the Archive")

        prefs = self.parent.app.prefs
        if prefs.has_key('USERNAME'):
            XRCCTRL(self, "TXT_USERNAME").SetValue(prefs['USERNAME'])

        if prefs.has_key('PASSWORD'):
            XRCCTRL(self, "TXT_PASSWORD").SetValue(prefs['PASSWORD'])
            
    def validate(self, event):
        if XRCCTRL(self, "CHK_SAVEPASSWD").GetValue():
            # save the username and password
            self.parent.app.prefs['USERNAME'] = XRCCTRL(self, "TXT_USERNAME").GetValue()
            self.parent.app.prefs['PASSWORD'] = XRCCTRL(self, "TXT_PASSWORD").GetValue()
        else:
            self.parent.app.prefs['USERNAME'] = ""
            self.parent.app.prefs['PASSWORD'] = ""
            
        return True
    
class DestWizPage(xrcwiz.XrcWizPage):
   def GetPrev(self):
      return self.prev

   def GetNext(self):
      if XRCCTRL(self, 'RDB_ARCHIVE').GetValue():
         target = self.parent.getPage('ARCHIVE_METADATA')
         self.parent.getPage('READY').SetNext(
             self.parent.getPage('FTP_PROGRESS'))
         self.parent.getPage('READY').SetPrev(
             self.parent.getPage('ARCHIVE_LOGIN'))
         self.parent.uploadingToArchive = True
         
      else:
         target = self.parent.getPage('VERIFICATION')
         self.parent.getPage('READY').SetNext(
             self.parent.getPage('VRDF'))
         self.parent.getPage('READY').SetPrev(
             self.parent.getPage('VERIFICATION'))

         self.parent.uploadingToArchive = False
         
      target.SetPrev(self)
      return target

class CcRest:
    """Wrapper class to decompose REST XML responses into Python objects."""
    
    def __init__(self, root):
        self.root = root

        self.__lc_doc = None

    def license_classes(self, lang='en'):
        """Returns a dictionary whose keys are license IDs, with the
        license label as the value."""

        lc_url = '%s/%s' % (self.root, 'classes')

        # retrieve the licenses document and store it
        self.__lc_doc = urllib2.urlopen(lc_url).read()

        # parse the document and return a dictionary
        lc = {}
        d = libxml2.parseMemory(self.__lc_doc, len(self.__lc_doc))
        c = d.xpathNewContext()

        licenses = c.xpathEval('//licenses/license')

        for l in licenses:
            lc[l.xpathEval('@id')[0].content] = l.content
            
        return lc
        
    def fields(self, license, lang='en'):
        """Retrieves details for a particular license."""

        l_url = '%s/license/%s' % (self.root, license)

        # retrieve the license source document
        self.__l_doc = urllib2.urlopen(l_url).read()

        d = libxml2.parseMemory(self.__l_doc, len(self.__l_doc))
        c = d.xpathNewContext()
        
        self._cur_license = {}
        keys = []
        
        fields = c.xpathEval('//field')

        for field in fields:
            f_id = field.xpathEval('@id')[0].content
            keys.append(f_id)
            
            self._cur_license[f_id] = {}

            self._cur_license[f_id]['label'] = field.xpathEval('label')[0].content
            self._cur_license[f_id]['description'] = \
                              field.xpathEval('description')[0].content
            self._cur_license[f_id]['type'] = field.xpathEval('type')[0].content
            self._cur_license[f_id]['enum'] = {}

            # extract the enumerations
            enums = field.xpathEval('enum')
            for e in enums:
                e_id = e.xpathEval('@id')[0].content
                self._cur_license[f_id]['enum'][e_id] = \
                     e.xpathEval('label')[0].content

        self._cur_license['__keys__'] = keys
        return self._cur_license

    def issue(self, license, answers, lang='en'):
        l_url = '%s/license/%s/issue' % (self.root, license)

        # construct the answers.xml document from the answers dictionary
        answer_xml = """
        <answers>
          <license-%s>""" % license

        for key in answers:
            answer_xml = """%s
            <%s>%s</%s>""" % (answer_xml, key, answers[key], key)

        answer_xml = """%s
          </license-%s>
        </answers>
        """ % (answer_xml, license)

        
        # retrieve the license source document
        try:
            self.__a_doc = urllib2.urlopen(l_url,
                                     data='answers=%s' % answer_xml).read()
        except urllib2.HTTPError:
            self.__a_doc = ''
            
        return self.__a_doc

class ChooserWizPage(wx.PyPanel):
    """Implements a license chooser page using CC REST API."""
    
    REST_ROOT = 'http://api.creativecommons.org/rest'
    STR_INTRO_TEXT="""With a Creative Commons license, you keep your copyright but allow people to copy and distribute your work provided the give you credit -- and only on the conditions you specify here.  If you want to offer your work with no conditions, choose the Public Domain."""

    HTML_LICENSE = '<html><body bgcolor="#%s"><font size="3">You chose <a href="%s">%s</a>.</font></body></html>'
    def __init__(self, parent, xrcid='CHOOSE_LICENSE'):
        wx.PyPanel.__init__(self, XRCCTRL(parent, "PNL_BODY"))

        self.xrcid = xrcid
        
        # initialize tracking attributes
        self._license_doc = None
        self.__license = ''
        self.__fields = []
        self.__fieldinfo = {}

        self.prev = self.next = None
        self.headline = 'Choose Your License'
        
        # create the web services proxy
        self.__cc_server = CcRest(self.REST_ROOT)
        
        # create the sizer
        self.sizer = wx.GridBagSizer(5, 5)
        self.SetSizer(self.sizer)

        self.sizer.Add(stext.StaticWrapText(parent=self,
                       label=self.STR_INTRO_TEXT),
                       (0,0), (1,1))

        # create the panel for the fields
        self.pnlFields = wx.Panel(self)
        self.sizer.Add(self.pnlFields, (2,0), (1,1),)
        # flag=wx.EXPAND|wx.ALL)

        # set up the field panel sizer
        self.fieldSizer = wx.FlexGridSizer(0, 2, 5, 5)
        self.fieldSizer.AddGrowableCol(1)
        self.pnlFields.SetSizer(self.fieldSizer)

        # create the basic widgets
        self.cmbLicenses = wx.ComboBox(self.pnlFields,
                                       style=wx.CB_DROPDOWN|wx.CB_READONLY
                                       )
        self.lblLicenses = stext.StaticWrapText(parent=self.pnlFields,
                                                label='License Class:')
        
        wx.CallAfter(self.getLicenseClasses)

        self.fieldSizer.Add(self.lblLicenses)
        self.fieldSizer.Add(self.cmbLicenses, flag=wx.EXPAND)

        # set up the license URL widget
        #self.txtLicense = stext.StaticWrapText(parent=self, label='')
        self.txtLicense = html.WebbrowserHtml(self, -1)
        self.txtLicense.SetPage(self.HTML_LICENSE % (html.BGCOLOR, 'foo', 'foo'))
        ir = self.txtLicense.GetInternalRepresentation()
        self.txtLicense.SetSize( (ir.GetWidth()+25, ir.GetHeight()+25) )

        self.sizer.Add(self.txtLicense, (3,0), (1,2), flag=wx.EXPAND)
        self.Layout()

        # bind event handlers
        self.Bind(wx.EVT_COMBOBOX, self.onSelectLicenseClass, self.cmbLicenses)

	self.Hide()

    def getLicenseClasses(self):
        """Calls the SOAP API via proxy to get a list of all available
        license class identifiers."""

        try:
            self.__l_classes = self.__cc_server.license_classes()
        except urllib2.URLError, e:
            wx.MessageBox("Unable to connect to the Internet to retrieve license information.  Check your connection and try again.",
                         caption="ccTag: Error.",
                         style=wx.OK|wx.ICON_ERROR, parent=self.GetParent())
            self.GetParent().Close()

        self.cmbLicenses.AppendItems(self.__l_classes.values())
        self.cmbLicenses.SetValue('Creative Commons')
        
        try:
            self.onSelectLicenseClass(None)
            self.updateLicense(None)
        except:
            pass
        
    def onLicense(self, event):
        """Submit selections and display license info."""
        answers = {}

        for field in self.__fields:
            if self.__fieldinfo[field]['type'] == 'enum':
                answer_list = [n for n in self.__fieldinfo[field]['enum'] if
                              self.__fieldinfo[field]['enum'][n] ==
                              self.__fieldinfo[field]['control'].GetValue()]
                if len(answer_list) > 0:
                    answer_key = answer_list[0]
                else:
                    return

                answers[field] = answer_key 

        self._license_doc = self.__cc_server.issue(self.__license, answers)

    def getLicenseUrl(self):
        """Extract the license URL from the returned licensing document."""
        if self._license_doc is None:
            return None

        try:
            d = libxml2.parseMemory(self._license_doc, len(self._license_doc))
            c = d.xpathNewContext()

            uri = c.xpathEval('//result/license-uri')[0].content
        except libxml2.parserError:
            return None

        return uri

    def getLicenseName(self):
        """Extract the license name from the returned licensing document."""
        if self._license_doc is None:
            return None

        try:
            d = libxml2.parseMemory(self._license_doc, len(self._license_doc))
            c = d.xpathNewContext()

            uri = c.xpathEval('//result/license-name')[0].content
        except libxml2.parserError:
            return None

        return uri
    
    def clearChooser(self):
        # delete everything except the license class chooser and label
        for child in self.pnlFields.GetChildren():
            if child != self.lblLicenses and child != self.cmbLicenses:
                child.Destroy()

        del self.__fieldinfo
        self.__fieldinfo = {}
        
    def onSelectLicenseClass(self, event):
        if event is not None and (
           event.GetString() == '' or \
           event.GetString() == self.__license):
            # bail out if there's no change; we'll get called again momentarily
            return

        if event is not None:
            license_str = event.GetString()
        else:
            license_str = self.cmbLicenses.GetValue()
            
        # get the new license ID
        self.__license = [n for n in self.__l_classes.keys()
                          if self.__l_classes[n] == license_str][0]
        
        # clear the sizer
        self.clearChooser()

        # retrieve the fields
        fields = self.__cc_server.fields(self.__license)
        self.__fields = fields['__keys__']
        self.__fieldinfo = fields

        for field in self.__fields:
            # update the UI
            self.updateFieldDetails(field)

        self.updateLicense(event)
        self.Layout()

    def updateFieldDetails(self, fieldid):
        
        field = fieldid

        self.__fieldinfo[field] = dict(self.__fieldinfo[field])

        # make sure we have a label
        if self.__fieldinfo[field]['label'] == '':
            self.__fieldinfo[field]['label'] = field

        # add the label text
        self.__fieldinfo[field]['label_ctrl'] = wx.StaticText(
            self.pnlFields,
            label=self.__fieldinfo[field]['label'])

        self.pnlFields.GetSizer().Add(self.__fieldinfo[field]['label_ctrl'])
        # add the control
        if self.__fieldinfo[field]['type'] == 'enum':
            # enumeration field; determine if we're using a combo or radio btns
            if len(self.__fieldinfo[field]['enum'].values()) > 3:
                # using a combo box
                self.__fieldinfo[field]['control'] = \
                     wx.ComboBox(self.pnlFields,
                                 style=wx.CB_DROPDOWN|wx.CB_READONLY,
                                 choices = self.__fieldinfo[field]['enum'].values()
                                 )

                self.__fieldinfo[field]['control'].SetToolTip(
                    wx.ToolTip(self.__fieldinfo[field]['description']))
                self.__fieldinfo[field]['control'].SetSelection(0)
                self.Bind(wx.EVT_COMBOBOX, self.updateLicense,
                          self.__fieldinfo[field]['control'])
                self.Bind(wx.EVT_TEXT, self.updateLicense,
                          self.__fieldinfo[field]['control'])
            else:
                # using radio buttons
                self.__fieldinfo[field]['control'] = wx.BoxSizer(wx.VERTICAL)
                
                # create the choice radio buttons
                first = True
                for e in self.__fieldinfo[field]['enum'].values():
                    if first:
                        rb = wx.RadioButton(self.pnlFields, -1, label=e,
                                            style=wx.RB_GROUP)
                        rb.SetValue(True)
                        first = False
                    else:
                        rb = wx.RadioButton(self.pnlFields, -1, label=e)

                    rb.SetToolTip(
                        wx.ToolTip(self.__fieldinfo[field]['description']))
                        
                    self.__fieldinfo[field]['control'].Add(rb)
                    self.Bind(wx.EVT_RADIOBUTTON, self.updateLicense, rb)

                # inject the GetValue method
                self.__fieldinfo[field]['control'].GetValue = \
                    lambda :self.GetCBValue(self.__fieldinfo[field]['control'])

            self.pnlFields.GetSizer().Add(
                self.__fieldinfo[field]['control'], flag=wx.EXPAND)

    def GetCBValue(self, radioSizer):
        for item in radioSizer.GetChildren():
            if item.GetWindow().GetValue():
                return item.GetWindow().GetLabel()
            
        return None
    
    def updateLicense(self, event):
        self.onLicense(event)
        self.txtLicense.SetPage(self.HTML_LICENSE % (html.BGCOLOR, self.getLicenseUrl(), self.getLicenseName()))
        # "You chose %s" % str(self.getLicenseName()))
                    
    def SetNext(self, next):
        self.next = next

    def GetNext(self):
        return self.next

    def SetPrev(self, prev):
        self.prev = prev

    def GetPrev(self):
        return self.prev

    def validate(self, event):
        self.onLicense(None)
        return True

