screens and the xml's for webradioFS
contact: plugins@fselbig.de

webradioFS.xml 
		class  WebradioFSScreen_13
		class  genre_anzeige_13
		class  menu_13
		groups_13
*************************************
wbrFS_r_site.xml
		right-site in screens, stream-info, Picture, logo ect
*************************************
wbrFS_setup.xml
	for 5 screens
		class  Fav_edit_13		-> Edit Streams
		class  WebradioFSSetup_13	-> Settings
		class  WebradioFS_FB_Setup_13	-> RC-Settings
		class  rec_menu_13		-> Record-Menu
		class  col_set_13  		-> set color-String in Color-Settings
*************************************
wbrfs_screensaver.xml
	for 2 screens
		class  wbrScreenSaver_13	-> screensaver 
		class  wbrfs_col_13		-> Color-Settings in screen
*************************************		
wbrFS_display.xml
	for Display 
		class webradioFSdisplay13
*************************************
wbrFS_dpsetup.xml
	for Display-Settings 
		class webradioFSsetDisplay
*************************************

Hauptmenu-Icon: <!--<convert type="MenuEntryCompare">webradioFS</convert>-->

########################################################

Details & Infos, for displays ect. as dictionary

from Plugins.Extensions.webradioFS.plugin import l4l_info

##########################################################		