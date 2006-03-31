#!/bin/sh

SOURCE='./build/Publisher'
FILEDEST='.'

VOLUMENAME=ccPublisher
IMAGENAME=$FILEDEST/$VOLUMENAME.dmg.sparseimage
DESTNAME=$FILEDEST/$VOLUMENAME.dmg

hdiutil create -srcfolder $SOURCE $DESTNAME

