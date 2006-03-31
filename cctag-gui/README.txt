cctools/ccTag-gui
updated 22 November 2004

*** Command line tools ***

Installing:
	$ python setup_cli.py install

Notes:
	The command line tools provide non-GUI access to the cctag libraries.

	* ccl.py provides an interface to lookup license claims embedded in
	  MP3 files.
	* cct.py inserts a license claim in an MP3 and generates the proper
	  verification RDF.
	* claim.py embeds a claim statement in an MP3 file.  No RDF is
 	  generated.

	Run any tool with --help for command line parameters.


*** GUI Tools ***
ccPublisher is a tool for embedding Creative Commons licenses in MP3 files,
generating license RDF for any file type, and uploading audio and
video files to the Internet Archive (archive.org) for free hosting.

ccPublisher may be run from the distribution directory.  Alternatively, the
.so support files may be placed anywhere on the system path.  The 
executable, cctag-wiz, and user interface definition, wizard.xrc, must remain
in the same directory.

Linux builds are still somewhat experimental; please report any problems
or suggestions to the author, Nathan Yergler <nathan@creativecommons.org>.
