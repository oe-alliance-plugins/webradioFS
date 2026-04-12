#!/usr/bin/python
# -*- coding: utf-8 -*-

class ext_l4l(object):
    __l4l_info = {}

    def get_l4l_info(self):
        return ext_l4l.__l4l_info

    def set_l4l_info(self, info):
        ext_l4l.__l4l_info = info  # {"Station":Station,"Fav":Fav,"Bitrate":Bitrate,"Genres":Genres,"logo":logo,"rec":rec,"akt_txt":akt_txt}
