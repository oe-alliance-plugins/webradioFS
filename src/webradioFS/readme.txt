
###########################
###########################
webradioFS API for webinterface

#######################################################
### --- webradioFS provides information as dic: --- ###
# Station = streamname
# Fav = Group-/Fav-Name
# rec = record on or off
# akt_txt = text from stream (Title, Interpret or whatever the Stream transmits)
# dictionary-Format:  l4l_info= {"Station":"","Fav":"","Bitrate":"","Genres":"","rec":0,"akt_txt":""}

#sample for import (python):
from Plugins.Extensions.webradioFS.ext import ext_l4l
WebRadioFS = ext_l4l() 
station=self.l4l_info.get("Station","") 
 
############################################
### --- start webradioFS:  --- ### 
sample: http://192.168.1.10:80/webradiofs/?cmd=starten

############################################
### --- exit webradioFS:  --- ### 
sample: http://192.168.1.10:80/webradiofs/?cmd=stoppen

############################################
### --- umschalten / toggle stream:  --- ### 
  /webradiofs/?stream=streamname
sample: http://192.168.1.10:80/webradiofs/?stream=Bayern%201

#################################################
### --- Gruppe umschalten /toggle group:  --- ###
  /webradiofs/?fav=Groupname
sample: http://192.168.1.10:80/webradiofs/?fav=my fav
 
 
 
 ######################
for skin's show readme in subdir /skin
