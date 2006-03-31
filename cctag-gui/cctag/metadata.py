"""Classes and functions to support embedding metadata in a music file;
contains the abstract class which allows extensions to be implemented for
OGG, etc.
"""

__id__ = "$Id$"
__version__ = "$Revision$"
__copyright__ = '(c) 2004, Creative Commons, Nathan R. Yergler'
__license__ = 'licensed under the GNU GPL2'

# use the bundled version of PyTagger,
# which contains our fixes.
import tagger
import cctag.const as const

class AudioMetadata:
    def __init__(self, filename):
        self.filename = filename

    def getTitle(self):
        raise NotImplementedError()

    def getArtist(self):
        raise NotImplementedError()

    def getYear(self):
        raise NotImplementedError()

    def getClaim(self):
        raise NotImplementedError()

    def setClaim(self, claim):
        raise NotImplementedError()
    
    def embed(self, license, verification, year, holder):
        """Embed a license claim in the audio file."""
        raise NotImplementedError()
    
class Mp3Metadata(AudioMetadata):
    def __init__(self, filename):
        AudioMetadata.__init__(self, filename)

        # create a handle for ID3v2
        try:
            self.__v2 = tagger.id3v2.ID3v2(self.filename,
                                           tagger.constants.ID3_FILE_MODIFY)
        except:
            self.__v2 = tagger.id3v2.ID3v2(self.filename,
                                           tagger.constants.ID3_FILE_NEW,
                                           version=2.3)

        # create a handle for ID3v1
        try:
            self.__v1 = tagger.id3v1.ID3v1(self.filename,
                                           tagger.constants.ID3_FILE_MODIFY)
            self.__hasV1 = True
        except tagger.exceptions.ID3HeaderInvalidException:
            self.__v1 = tagger.id3v1.ID3v1(self.filename,
                                           tagger.constants.ID3_FILE_NEW)
            self.__hasV1 = False

    def _getFrame(self, fids):
        """Returns the first frame whose ID is contained in the tuple fids.
        Returns None if the frame identifiers do not exist."""

        for frame in self.__v2.frames:
            if frame.fid in fids:
                return frame

        return None

    def _getFrameData(self, fids):

        # retrieve the frame
        frame = self._getFrame(fids)

        if frame is not None and len(frame.strings) > 0:
            return frame.strings[0]
        
        return None
    
    def getTitle(self):
        return self._getFrameData(('TT2', 'TIT2')) or \
               self.__v1.songname

    def getArtist(self):
        return self._getFrameData(('TP1', 'TPE1')) or \
               self.__v1.artist

    def getYear(self):
        return self._getFrameData(('TYE', 'TYER', 'TDRC')) or \
               self.__v1.year

    def getClaim(self):
        return self._getFrameData(('TCR', 'TCOP')) or ''
    
    def _needsUpgrade(self):
        """Returns True if a file has ID3 tags of v2.2."""

        return (self.__v2.version == 2.2)
        
    def upgrade(self):
        """Upgrades a file's ID3 tags from ID3v2.2 to ID3v2.3."""

        # retrieve the existing frames
        oldframes = {}
        for frame in self.__v2.frames:
            oldframes[frame.fid] = (frame.rawdata, frame.length)
            
        # re-open the file for writing
        self.__v2 = tagger.id3v2.ID3v2(self.filename,
                                       mode=tagger.constants.ID3_FILE_NEW,
                                       version=2.3)
        
        # rewrite each frame
        for fid in oldframes:
            if fid not in const.TAG_MAP or const.TAG_MAP[fid] is None:
                # no mapping for this tag
                print "Field can not be converted from 2.2 to 2.3: ", fid
                continue

            newframe = self.__v2.new_frame(fid=const.TAG_MAP[fid])
            newframe.rawdata, newframe.length = oldframes[fid]
            
            newframe.parse_field()

            self.__v2.frames.append(newframe)

        self.__v2.commit()

    def _addId3v1(self):
        """Checks for the existance of ID3v1 data in the specified file;
        if it does not exist, generates data from the ID3v2 tags.
        """

        if self.__hasV1:
            return

        self.__v1.songname = self.getTitle()
        self.__v1.artist = self.getArtist()
        self.__v1.year = self.getYear()

        # save the changes
        self.__v1.commit()

        # reload our v1 handle
        self.__v1 = tagger.id3v1.ID3v1(self.filename,
                                       tagger.constants.ID3_FILE_MODIFY)
        
        self.__hasV1 = True
        

    def setClaim(self, claim):

        # check if an upgrade to 2.3 is needed before embedding
        if (self._needsUpgrade()):
            self.upgrade()

        # set the TCOP frame
        tcop = self._getFrame('TCOP')
        if tcop is None:
            tcop = self.__v2.new_frame('TCOP')
            self.__v2.frames.append(tcop)

        tcop.encoding = 'utf_8'
        tcop.strings = [claim]

        self.__v2.commit()
        
    def embed(self, license, verification, year, holder):
        
        # first generate the embedded license claim str
        claim = "%s %s. Licensed to the public under %s verify at %s" % (
            year, holder, license, verification )

        self.setClaim(claim)
        
        # add ID3v1 if necessary
        self._addId3v1()

    
class OggMetadata(AudioMetadata):
    pass

meta_handlers = {'mp3':Mp3Metadata,
                 'ogg':OggMetadata,
                 }
                
def metadata(filename):
    """Returns the appropriate instance for the detected filetype of
    [filename].  The returned instance will be a subclass of the
    AudioMetadata class."""

    # XXX right now we do stupid name-based type detection; a future
    # improvment might actually look at the file's contents.
    ext = filename.split('.')[-1].lower()
    if ext in meta_handlers:
        return meta_handlers[ext](filename)
    else:
        # fall back to AudioMetadata, which will raise NotImplementedErrors
        # as necessary
        return AudioMetadata(filename)

