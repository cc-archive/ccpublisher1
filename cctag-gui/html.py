import webbrowser

import wx.html

class WebbrowserHtml(wx.html.HtmlWindow):
    def OnLinkClicked(self, linkinfo):
        webbrowser.open( linkinfo.GetHref(), True, True )

BGCOLOR = "efefef"

MORE_INFO = """
<html>
<title>ccPublisher</title>
<body bgcolor="#e3e3e3">
<table width="100%%" bgcolor="#729cb3" cellspacing="0" border="0">
<tr><td><font size="+1"><strong>ccPublisher</strong></font><br>
        <font size="-1">version %s</font></td>
    <td align="right"><img src="%s"></td></tr>
</table>
<p><strong>What is ccPublisher?</strong></p>
<p>ccPublisher is a tool which will help you put your audio and video on the
Web with a Creative Commons license.  It will also let you upload your files
to the Internet Archive to take advantage of free hosting.</p>
<p><strong>What files can ccPublisher upload?</strong></p>
<p>ccPublisher will embed a license claim in MP3 audio files.  ccPublisher will let
you upload any audio or video file to the Internet Archive.</p>
<p><strong>What about file sharing networks?</strong></p>
<p>MP3 files licensed using ccPublisher (uploaded to the Internet Archive or self-
hosted) will have an embedded license tag added which some file sharing networks
can detect.  Just drop the files in your shared folder after you finish the
ccPublisher wizard.</p>
<p><strong>Do I need an Internet connection?</strong></p>
<p>Yes, ccPublisher uses Creative Commons web services to create license
information for your files.</p>
</body>
</html>

"""

class HtmlHelp(wx.Dialog):
    def __init__(self, parent, title, source):
        wx.Dialog.__init__(self, parent, -1, title,)
        html = WebbrowserHtml(self, -1, size=(420, -1))
        if "gtk2" in wx.PlatformInfo:
            html.SetFonts('','',[wx.html.HTML_FONT_SIZE_1,
                                 wx.html.HTML_FONT_SIZE_2,
                                 10,
                                 wx.html.HTML_FONT_SIZE_4,
                                 wx.html.HTML_FONT_SIZE_5,
                                 wx.html.HTML_FONT_SIZE_6,
                                 wx.html.HTML_FONT_SIZE_7,
                                 ]
                          )
        #    html.NormalizeFontSizes()
        html.SetPage(source)
        btn = html.FindWindowById(wx.ID_OK)
        ir = html.GetInternalRepresentation()
        html.SetSize( (ir.GetWidth()+25, ir.GetHeight()+25) )
        self.SetClientSize(html.GetSize())
        self.CentreOnParent(wx.BOTH)

