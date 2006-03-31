import tagger as pyid3v2 
import sys

id3 = pyid3v2.id3v2.ID3v2(sys.argv[-1], pyid3v2.constants.ID3_FILE_READ)
for f in id3.frames:
    print f.fid
    print f.strings

