# -*- coding: utf-8 -*-
from html import escape
import os
import random
from urllib.parse import quote

import Screens.Standby
from Components.VolumeControl import VolumeControl
from Tools.Directories import copyfile
from enigma import eDVBVolumecontrol, eTimer
from twisted.web import resource

from . import _, __version__
from .wbrfs_funct import read_einzeln

fp = read_einzeln().reading(
    (("audiofiles", "audiopath"), ("audiofiles", "save_random"), ("opt", "audiofiles"), ("prog", "DPKG"))
)

audiopath = fp[0]
save_random = fp[1]
audiofiles = fp[2]
try:
    DPKG = fp[3]
except Exception:
    DPKG = False


def run_webradioFS(session=None):
    from .plugin import restarter2

    return restarter2()


def _s(value):
    # backend lists may contain bytes
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value)


def playlist_read(playlist):
    # returns [length, title, path] entries of an extended m3u file
    pl = []
    try:
        with open(playlist, encoding="utf-8", errors="replace") as f:
            title = None
            length = "-1"
            for line in f:
                line = line.strip()
                if not line or line == "#EXTM3U":
                    continue
                if line.startswith("#EXTINF:"):
                    sp = line[8:].split(",", 1)
                    if len(sp) == 2:
                        length, title = sp[0].strip(), sp[1].strip()
                elif not line.startswith("#"):
                    path = line if line.startswith("/") else os.path.normpath(os.path.join(os.path.dirname(playlist), line))
                    pl.append([length, title or os.path.splitext(os.path.basename(line))[0], path])
                    title = None
                    length = "-1"
    except OSError:
        pass
    return pl


def playlist_write(playlist, entries):
    with open(playlist, "w", encoding="utf-8") as f:
        f.write("#EXTM3U")
        for x in entries:
            f.write(f"\n#EXTINF:{x[0]},{x[1]}\n{x[2]}")


LINK = 'style="color:#ffffff;text-decoration:none;font-size:1.2em"'
ADD = 'style="color:yellow;text-decoration:none;font-size:1.2em"'
BGR = "background-repeat:repeat-y;background-image:url(/webradiofs/skin/images/webif_bgr.png)"
IMG = "/webradiofs/skin/images/"


class webradioFSweb(resource.Resource):
    title = "webradioFS Webinterface"
    isLeaf = True
    RestartGUI = False

    def __init__(self):
        super().__init__()
        self.volctrl = eDVBVolumecontrol.getInstance()
        self.stream = None
        self.fav = None
        self.search_on = None
        self.fav_list = ()
        self.findliste = []
        self.sel_fav = ""
        self.liste1 = ()
        self.playlist = "0"
        self.playlistfile = "/tmp/wbrfs_playlist"
        self.plugin_run = False
        self.l4l_info = None
        self.akt_time = "20"
        self.akt_Play_nr = 0
        self.searchdir = audiopath
        self.search_art = "fi"
        self.check_timer = eTimer()
        if DPKG:
            self.check_timer_conn = self.check_timer.timeout.connect(self.action)
        else:
            self.check_timer.callback.append(self.action)
        os.makedirs("/etc/ConfFS", exist_ok=True)
        open("/tmp/wbrfs_playlist", "a").close()
        for i in range(5):
            open(f"/etc/ConfFS/playlist{i + 1}.m3u", "a").close()

    def render_GET(self, request):
        return self.action(request).encode("utf-8")

    def render_POST(self, request):
        return self.action(request).encode("utf-8")

    def vol_set(self, vol):
        if vol == "mute":
            VolumeControl.instance.volMute()
        elif vol == "minus":
            VolumeControl.instance.volDown()
        elif vol == "plus":
            VolumeControl.instance.volUp()

    def _info(self):
        return self.l4l_info or {}

    def _add_entries(self, f, items):
        # items: (title, path) pairs
        for title, path in items:
            if not title.endswith(".m3u"):
                f.write(f"#EXTINF:-1,{title}\n{path}\n")

    def _shuffle(self, items):
        items = list(items)
        if str(save_random) == "True" or save_random == "random":
            random.shuffle(items)
        return items

    def _handle_add(self, add):
        from .webradioFS import file_list2

        prefix = ""
        if os.path.isfile(self.playlistfile):
            with open(self.playlistfile, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            if not lines:
                prefix = "#EXTM3U\n"
            elif lines[-1].strip():
                prefix = "\n"
        else:
            prefix = "#EXTM3U\n"
        with open(self.playlistfile, "a", encoding="utf-8") as f:
            f.write(prefix)
            if add == "all2":
                self._add_entries(f, [(_s(x[0]), _s(x[1])) for x in self._shuffle(self.findliste)])
            elif add == "all":
                self._add_entries(f, [(_s(x[0]), _s(x[1])) for x in self._shuffle(self.liste1) if x[7] == "Files"])
            else:
                se = add.split(";.;")
                if len(se) == 3:
                    if se[2].lower() == "files":
                        self._add_entries(f, [(se[0], se[1])])
                    else:
                        nliste = self._shuffle(file_list2([se[1]], "fi2").Dateiliste)
                        self._add_entries(f, [(_s(x[0]), _s(x[1])) for x in nliste])

    def _handle_del(self, entf):
        if not os.path.isfile(self.playlistfile):
            return
        if entf == "1":
            open(self.playlistfile, "w").close()
            return
        entries = playlist_read(self.playlistfile)
        if entf.startswith("i:") and entf[2:].isdigit():
            idx = int(entf[2:])
            entries = [x for n, x in enumerate(entries) if n != idx]
        elif entf.startswith("p:"):
            entries = [x for x in entries if x[2] != entf[2:]]
        else:
            return
        playlist_write(self.playlistfile, entries)
        if self.sel_fav.startswith(_("Playlist")):
            from .plugin import list_play

            list_play((self.akt_Play_nr, self.playlistfile))

    def _handle_stream(self, stream):
        from . import plugin

        if stream.endswith("/"):
            plugin.playdir2(stream)
        elif stream.endswith(".m3u"):
            self.fav = _("Playing from *.m3u")
            self.playlistfile = stream
            plugin.list_play((8, stream))
        else:
            plugin.umschalt(stream)
            self.stream = stream
            if stream.startswith("/"):
                self.searchdir = os.path.dirname(stream)
            elif stream.startswith(".."):
                self.searchdir = audiopath

    def _handle_command(self, command, running):
        from . import plugin

        self.akt_time = "5"
        if command == "starten":
            if not running:
                self.plugin_run = True
                run_webradioFS(self)
        elif command == "stoppen":
            self.plugin_run = False
            self.l4l_info = None
            self.search_on = None
            plugin.abschalt()
        elif command == "box_on" and Screens.Standby.inStandby:
            self.l4l_info = None
            plugin.standby_toggle(self)
        elif command == "play_in_standby" and Screens.Standby.inStandby:
            self.l4l_info = None
            plugin.play_in_standby(self)

    def _handle_args(self, args, running):
        from . import plugin

        if "list_num" in args:
            self.playlist = args["list_num"]
        if self.playlist == "0":
            self.playlistfile = "/tmp/wbrfs_playlist"
        else:
            self.playlistfile = f"/etc/ConfFS/playlist{self.playlist}.m3u"

        self.fav = None
        if "vol0.y" in args:
            self.vol_set("mute")
        elif "volm.y" in args:
            self.vol_set("minus")
        elif "volp.y" in args:
            self.vol_set("plus")
        elif "einzelstream" in args:
            plugin.einzelplay(args["einzelstream"].split(";.;"))
        elif "search_on" in args:
            if self.search_on:
                self.search_on = None
                self.findliste = []
            else:
                self.search_on = 1
        elif "playdir" in args:
            plugin.playdir(args["playdir"])
        elif "stream" in args:
            self._handle_stream(args["stream"])
        elif "list_play" in args:
            value = args["list_play"]
            if value == "stop":
                plugin.play_stop(1)
            elif value == "rec":
                plugin.webrec()
            elif value.isdigit():
                plugin.list_play((int(value), self.playlistfile))
                self.akt_Play_nr = int(value)
        elif "fav" in args:
            if args["fav"] != _("Search"):
                plugin.fav_wechsel(args["fav"])
            self.fav = args["fav"]
        elif "add" in args:
            self._handle_add(args["add"])
        elif "entf" in args:
            self._handle_del(args["entf"])
        elif "clear" in args:
            self.findliste = []
        elif "search" in args:
            from .webradioFS import file_list2

            art = args.get("art", "")
            sdir = args.get("sdir", "")
            text = args.get("searchtxt", "").strip().lower()
            self.search_art = art
            if art and sdir and text:
                self.findliste = list(file_list2([sdir], art, 1, text).Dateiliste)
        elif "cmd" in args:
            self._handle_command(args["cmd"], running)
        self.akt_time = "5"

    def action(self, req=None):
        from . import plugin, webradioFS as wbr

        running = plugin.running
        self.check_timer.stop()
        if req is not None:
            req.setHeader("Content-type", "text/html; charset=UTF-8")
            args = {k.decode("utf-8", "ignore"): v[0].decode("utf-8", "replace") for k, v in (req.args or {}).items() if v}
            if args:
                self._handle_args(args, running)
            else:
                self.check_timer.startLongTimer(20)
            running = plugin.running
        logo = None
        stream = None
        text = ""
        l4l = None
        if running:
            self.fav_list = wbr.web_liste_favs
            self.liste1 = wbr.web_liste_streams
            try:
                from Plugins.Extensions.webradioFS.ext import ext_l4l

                l4l = ext_l4l()
                info = l4l.get_l4l_info()
                if self.l4l_info != info:
                    self.l4l_info = info
                    self.akt_time = "5"
            except Exception:
                l4l = None
                self.l4l_info = None
            info = self._info()
            if l4l:
                if info.get("Logo", "") and os.path.isfile(info.get("Logo", "")):
                    logo = info["Logo"]
                    try:
                        copyfile(logo, "/usr/lib/enigma2/python/Plugins/Extensions/webradioFS/data/logo.png")
                    except Exception:
                        logo = None
                if info.get("Station", ""):
                    stream = info["Station"]
                text = info.get("akt_txt", "")
        return self._render(running, stream, logo, text, l4l)

    def _render(self, running, stream, logo, text, l4l):
        info = self._info()
        volume = VolumeControl.instance.volctrl.getVolume()
        mute = VolumeControl.instance.volctrl.isMuted()
        color = "#696969" if mute else "#00CD00"
        redirect = self.akt_time == "5"
        h = [
            "<html>\n<head>",
            '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">',
            '<meta http-equiv="cache-control" content="no-cache"><meta http-equiv="pragma" content="no-cache">',
            '<meta http-equiv="expires" content="0">',
            f'<meta http-equiv="refresh" content="{self.akt_time}">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f'<link rel="shortcut icon" href="{IMG}favicon.ico">',
            "<title>webradioFS-webinterface</title>",
            "<style>",
            f'div.line{{border:0;background-image:url("{IMG}webif_line.png");background-repeat:no-repeat;width:640px;height:10px}}',
            "div.fsb{position:relative;left:420px;top:-23px;border:1px solid #000;background-color:#8A8A8A;width:150px;height:6px;padding:1px}",
            f"div.fortschritt{{background-color:{color};height:6px;width:{int(volume)}%}}",
            "</style>",
            '<script>function load(){window.location.replace("../webradiofs");}</script>',
            "</head>",
        ]
        if redirect:
            self.akt_time = "20"
            h.append('<body onload="load()" bgcolor="#666666" text="#FFFFFF">')
        else:
            h.append('<body bgcolor="#666666" text="#FFFFFF">')
        h.append('<div style="width:100%">')
        h.append(f'<div style="width:600px;{BGR}">')
        h.append(f'<table width="600"><tr><td colspan="3" style="text-align:center"><br><img border="0" src="{IMG}webif.png"></td></tr>')
        h.append(f'<tr><td width="200"></td><td width="200" style="text-align:center;vertical-align:bottom"><b><i>Version: {escape(__version__)}</i></b></td></tr></table>')
        h.append('<div class="line"></div></div>')
        h.append(f'<div style="font-size:1.4em;width:600px;text-align:center;{BGR}">')
        if Screens.Standby.inStandby:
            h.append("<span><b>Box in standby....</b></span><br><br>")
            h.append(self._button("box_on", _("toggle standby"), "green", 314))
            h.append('<span><br></span><div class="line"></div>')
        else:
            h.append('<div style="padding-top:3px;height:64px;padding-left:10px;float:left;width:350px">')
            if not running:
                h.append(self._button("starten", _("start webradioFS"), "green", 313))
            else:
                h.append(self._button("stoppen", _("exit webradioFS"), "red", 313))
            h.append("</div>")
            h.append('<div style="height:55px;padding-right:30px;text-align:right"><div style="height:46px;padding-top:5px">')
            h.append(
                '<form method="post">'
                f'<input name="vol0" aria-label="{escape(_("Mute"))}" type="image" src="{IMG}mute.png">&nbsp;&nbsp;'
                f'<input name="volm" aria-label="{escape(_("Volume Down"))}" type="image" src="{IMG}Leise.png">&nbsp;&nbsp;'
                f'<input name="volp" aria-label="{escape(_("Volume Up"))}" type="image" src="{IMG}Laut.png"></form>'
            )
            h.append('<div class="fsb"><div class="fortschritt"></div></div></div></div>')
            h.append('<div style="clear:left"></div><div class="line"></div></div>')
            if l4l and info.get("Fav", ""):
                self.sel_fav = info["Fav"]
            if l4l and stream and running:
                self._render_station(h, stream, logo, text)
            no_found = False
            if len(self.fav_list) and running and info.get("rec", "") != 1:
                no_found = self._render_groups(h)
            if len(self.liste1) and running and not no_found:
                self._render_list(h, stream)
            elif self.sel_fav == _("No group selected") and running:
                h.append(f'<div style="font-size:1.4em;text-align:center;height:50px;width:600px">{escape(_("save in favorites for all functions"))}...</div>')
        h.append("</div></div></body></html>")
        return "\n".join(h)

    def _button(self, cmd, label, color, width):
        label = escape(label)
        return (
            f'<form autocomplete="off" method="GET"><input type="hidden" name="cmd" value="{cmd}">'
            f'<input type="button" aria-label="{label}" style="width:{width}px;height:54px;font-size:1.4em;'
            f'background-image:url({IMG}button_{color}.png)" value="{label}" onclick="this.form.submit()"></form>'
        )

    def _render_station(self, h, stream, logo, text):
        info = self._info()
        h.append(f'<div style="width:600px;{BGR}">')
        h.append('<div style="text-align:left;padding:3px 0 3px 10px;width:340px;float:left"><nobr>')
        liste = info.get("liste")
        if info.get("Genres", "") != _("wbrfsfiles"):
            h.append(f"Stream: {escape(info.get('Station', ''))}<br>")
            h.append(f"{escape(info.get('art', ''))} {escape(info.get('Fav', ''))}<br>")
            h.append(f"Bitrate: {escape(str(info.get('Bitrate', '')))}<br>")
            h.append(f"Genre(s): {escape(info.get('Genres', ''))}")
            if liste:
                self.sel_fav = liste
        else:
            fav_info = info.get("Fav", "")
            if liste:
                self.sel_fav = liste
            elif fav_info.startswith(_("Playing from folder")):
                self.sel_fav = _("Playing from folder")
                self.fav = _("Playing from folder")
            elif fav_info == "Playlist 8" or fav_info.endswith(".m3u"):
                self.fav = _("Playing from *.m3u")
            elif self.fav:
                try:
                    self.sel_fav = self.fav_list[0] if self.liste1[0][7] == "radio" else _("My files")
                except (IndexError, TypeError):
                    pass
            if self.fav == _("Playing from *.m3u"):
                h.append(f"<b>{escape(_('m3u:'))}</b> {escape(fav_info.replace(_('Files from'), ''))}<br>")
                self.stream = info.get("akt_txt", "")
            elif self.fav and not self.fav.startswith(_("Playing")):
                h.append(f"<b>{escape(_('Group:'))}</b> {escape(fav_info)}<br>")
                self.sel_fav = fav_info
            d1 = info.get("Station", "")
            dir2 = os.path.dirname(d1).split("/")
            dir2 = f"... /{dir2[-2]}/{dir2[-1]}" if len(dir2) > 2 else d1
            h.append(f"<b>Dir:</b> {escape(dir2)}<br><b>Typ:</b> {escape(info.get('art', ''))}")
            if info.get("Len", ""):
                h.append(f"<br><b>Len:</b> {escape(str(info['Len']))}")
        h.append("</nobr></div>")
        h.append(f'<div align="right" style="float:left;text-align:right"><img border="0" src="{"/webradiofs/data/logo.png" if logo else IMG + "webif_logo.png"}"></div>')
        h.append('<div style="clear:left"></div>')
        if info.get("akt_txt", ""):
            shown = info["akt_txt"] if info.get("art", "") != "dir" else text
            h.append(f'<div align="center" style="width:600px;{BGR}"><span style="color:#E0FFFF;font-size:1.2em">{escape(shown)}</span></div>')
        h.append('<div class="line"></div>')

    def _render_groups(self, h):
        if self.fav:
            self.sel_fav = self.fav
        no_found = self.sel_fav == _("No group selected")
        h.append(f'<div style="font-size:1.4em;text-align:left;height:50px;padding-left:10px;padding-top:10px;width:100%;{BGR}">')
        h.append('<form name="group" autocomplete="off" method="GET">')
        h.append(f'{escape(_("Group:"))} <select name="fav" onchange="this.form.submit()" style="background-color:#99CCFF;font-size:1em">')
        h.append(f'<option selected="selected">{escape(self.sel_fav)}</option>')
        seen = []
        for x in self.fav_list:
            x = _s(x)
            if x not in seen and x not in (self.sel_fav, _("No group selected"), _("Genres")):
                h.append(f"<option>{escape(x)}</option>")
                seen.append(x)
        h.append('</select></form></div><div class="line"></div>')
        return no_found

    def _row_icon(self, x, stream, rec_html):
        info = self._info()
        kind = x[7]
        icon = "pic_ok.png"
        if x[0] == stream or (int(x[4]) > 29 and info.get("Station", "") == x[1]):
            icon = "pic_play.png"
            rec_html = f'</td><td width="35"><a href="?list_play=rec"><img src="{IMG}webifrec.png" width="28" height="28" border="0" alt="Stop"></a>'
        elif kind == "Dir1":
            self.searchdir = x[2]
            icon = "up.png"
        elif int(x[4]) > 29 and kind != "Dir":
            icon = "pic_play.png" if info.get("Fav", "") == "Playlist 8" and x[0] == self.stream else "audiofile.png"
        elif int(x[3]) > 0 and kind != "Dir":
            icon = "pic_err.png"
        return icon, rec_html

    def _render_list(self, h, stream):
        info = self._info()
        rec = info.get("rec", "")
        h.append(f'<div style="width:600px;{BGR}"><table style="width:100%;{BGR}">')
        if audiofiles and self.sel_fav == _("My files"):
            h.append(
                f'<tr><td width="30"></td><td width="35">&nbsp;<a href="?add=all" {ADD}>add</a></td>'
                f"<td> {escape(_('all visible files (not folder)'))}</td></tr>"
            )
        for x in self.liste1:
            x = [_s(v) if isinstance(v, bytes) else v for v in x]
            if x[0].startswith("@") or x[0] == "..autofs":
                continue
            rec_html = '</td><td width="35">&nbsp;&nbsp;'
            if x[7] == "Dir":
                h.append(f'<tr><td width="30"><a href="?playdir={quote(x[1])}" {LINK}><img border="0" src="{IMG}dir.png"></a>')
            else:
                icon, rec_html = self._row_icon(x, stream, rec_html)
                h.append(f'<tr><td width="30"><img border="0" src="{IMG}{icon}">')
            if x[7] in ("Dir", "Files"):
                stra = quote(f"{x[0]};.;{x[1]};.;{x[7]}")
                if x[1].endswith(".m3u") or str(self.playlist) == "7":
                    if info.get("art", "") == _("file") and x[0] == os.path.basename(self.playlistfile):
                        h.append(f'</td><td width="35"><img border="0" src="{IMG}pic_play.png">')
                    else:
                        h.append('</td><td width="35">&nbsp;')
                elif not self.sel_fav.startswith(_("Playlist")):
                    h.append(f'</td><td width="35">&nbsp;<a href="?add={stra}" {ADD}>add</a>')
                else:
                    h.append(f'</td><td width="35">&nbsp;<a href="?entf={quote("p:" + x[1])}" {ADD}>del</a>')
            else:
                h.append(rec_html)
            name = escape(x[0])
            if rec != 1:
                target = x[1] if (x[0].endswith(".m3u") or x[7] == "Dir") else x[0]
                h.append(f'</td><td><a href="?stream={quote(target)}" {LINK}> {name} </a>')
            else:
                h.append(f'</td><td style="color:#ffffff;font-size:1.2em"> {name}')
            if x[0] == stream and rec == 1:
                h.append(f' <img border="0" src="{IMG}rec1.png">')
            elif x[0] == stream and rec == 2:
                h.append(f' <img border="0" src="{IMG}rc1.png">')
            h.append("</td></tr>")
        h.append('</table><div class="line"></div>')
        if audiofiles:
            self._render_search(h)
            self._render_playlists(h)
        h.append("</div>")

    def _render_search(self, h):
        info = self._info()
        h.append(f'<div style="width:600px;{BGR}">')
        if info.get("liste") and self.searchdir and info.get("liste") == _("My files"):
            h.append(f'<div style="font-size:1.4em;text-align:center;{BGR}"><a style="font-size:1.2em;color:#6495ED" href="?search_on=1">search</a>')
            h.append(f'<form method="GET"><input type="hidden" name="sdir" value="{escape(self.searchdir, quote=True)}">')
            h.append(f'<table style="width:100%"><tr><td colspan="3" align="left">in: {escape(self.searchdir)}</td></tr><tr><td></td><td>')
            for label, art in (("Files", "fi"), ("Folder", "fo"), ("Files+Folder", "fifo")):
                chk = ' checked="checked"' if art == self.search_art else ""
                h.append(f'<input type="radio" name="art" value="{art}"{chk}> {label}')
            h.append('</td><td align="right"><input type="submit" name="clear" value="clear list"></td></tr><tr>')
            h.append(
                '<td style="font-size:1.2em">Search term: </td><td><input style="font-size:1.4em;background-color:#99CCFF" '
                'name="searchtxt" type="text" size="26" maxlength="50"></td>'
                '<td align="right"><input type="submit" name="search" value="Start">&nbsp;&nbsp;</td></tr></table></form>'
            )
            if self.findliste:
                h.append('<div class="line"></div>')
                h.append(f'<div style="font-size:1em;text-align:left;color:#E0FFFF;{BGR}"><table style="width:100%">')
                h.append(
                    f'<tr><td width="30"></td><td width="35">&nbsp;<a href="?add=all2" {ADD}>add</a></td>'
                    f"<td> {escape(_('all visible files and all files in folder'))}</td></tr>"
                )
                for x in self.findliste:
                    if len(x) > 7 and x[7] in ("Dir", "Files"):
                        name, path = _s(x[0]), _s(x[1])
                        icon = "dir.png" if x[7] == "Dir" else "audiofile.png"
                        stra = quote(f"{name};.;{path};.;{x[7]}")
                        h.append(
                            f'<tr><td width="30"><img border="0" src="{IMG}{icon}"></td>'
                            f'<td width="35">&nbsp;<a href="?add={stra}" {ADD}>add</a></td>'
                            f'<td><a href="?einzelstream={stra}" {LINK}> {escape(name)} </a></td></tr>'
                        )
                h.append("</table></div>")
            h.append("</div>")
            h.append('<div class="line"></div>')
        h.append("</div>")

    def _render_playlists(self, h):
        h.append(f'<div style="font-size:1.2em;text-align:center;color:#E0FFFF;{BGR}">Play-List: ')
        akt_list = "-1"
        for i in range(6):
            u1 = u2 = ""
            if str(i) == self.playlist:
                color = "yellow"
                akt_list = self.playlist
                u1, u2 = "<u>", "</u>"
            else:
                path = "/tmp/wbrfs_playlist" if i == 0 else f"/etc/ConfFS/playlist{i}.m3u"
                color = "green" if playlist_read(path) else "#ffffff"
            label = " temp " if i == 0 else str(i)
            h.append(
                f'&nbsp;&nbsp;&nbsp;&nbsp;<a href="?list_num={i}" style="color:{color};text-decoration:none;font-size:1.4em">{u1}{label}{u2}</a>'
            )
        h.append(
            f'&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href="?list_play={int(self.playlist) + 1}"><img src="{IMG}lPlay.png" width="28" height="28" border="0" alt="Play"></a>'
            f'&nbsp;&nbsp;&nbsp;&nbsp;<a href="?list_play=stop"><img src="{IMG}lStop.png" width="28" height="28" border="0" alt="Stop"></a></div>'
        )
        h.append('<div class="line"></div>')
        if self.fav == _("Playing from *.m3u") or (os.path.isfile(self.playlistfile) and f"{_('Playlist')} {akt_list}" != self.sel_fav):
            entries = playlist_read(self.playlistfile)
            if entries:
                info = self._info()
                h.append(f'<table style="width:100%;{BGR}">')
                h.append(
                    f'<tr><td width="25" align="left"><a href="?entf=1" {ADD}>del</a></td><td></td>'
                    f'<td align="left" style="font-size:1.2em">{escape(_("all (del all entries)"))}</td></tr>'
                )
                for n, x in enumerate(entries):
                    stra = quote(f"{x[1]};.;{x[2]};.;Files;.;{self.playlistfile};.;{int(self.playlist) + 1}")
                    play = f'<img border="0" src="{IMG}pic_play.png">' if info.get("Station", "") == x[2] else "&nbsp;"
                    h.append(f'<tr><td width="25" align="left"><a href="?entf=i:{n}" {ADD}>del</a></td><td>{play}</td>')
                    if x[1].endswith(".m3u"):
                        h.append(f'<td><a href="?stream={quote(x[2])}" {LINK}> {escape(x[1])} </a></td></tr>')
                    else:
                        h.append(f'<td><a href="?einzelstream={stra}" {LINK}>&nbsp;&nbsp;{escape(x[1])} </a></td></tr>')
                h.append("</table>")
            else:
                name = "temp" if self.playlist == "0" else self.playlist
                msg = _("contains no audio files\nor is incorrectly formatted").replace("\n", "<br>")
                h.append(f'<div style="font-size:1.4em;text-align:center;height:50px;width:600px">{escape(_("Playlist"))} {name} {msg}</div>')
            h.append('<div class="line"></div>')
