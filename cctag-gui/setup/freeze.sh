#!/bin/bash

export cxpath=/opt/cx_Freeze-3.0
export APPNAME=cctag
export DISTDIR=$APPNAME-$1

mkdir $DISTDIR

$cxpath/FreezePython --install-dir=$DISTDIR ../cctag-wiz.py
cp ../*.xrc $DISTDIR
cp ../LICENSE $DISTDIR
cp ../README.txt $DISTDIR

tar czvf $APPNAME-$1.tgz $DISTDIR

rm -rf $DISTDIR

