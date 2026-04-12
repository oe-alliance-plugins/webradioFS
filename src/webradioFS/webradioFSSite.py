# -*- coding: utf-8 -*-
from html import escape
import os

import Screens.Standby
from Components.VolumeControl import VolumeControl
from Tools.Directories import copyfile
from enigma import eDVBVolumecontrol, eTimer
from twisted.web import resource

from . import _
from . import webradioFS
from .plugin import myversion
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


class webradioFSweb(resource.Resource):
    title = "webradioFS Webinterface"
    isLeaf = True
    RestartGUI = False

    def __init__(self):
        super().__init__()
        self.volctrl = eDVBVolumecontrol.getInstance()
        self.com_vol = int(self.volctrl.getVolume())
        self.l4l_info = None
        self.akt_time = "20"
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

    def _read_status(self):
        info = {}
        logo = None
        try:
            from Plugins.Extensions.webradioFS.ext import ext_l4l

            l4l = ext_l4l()
            info = l4l.get_l4l_info() or {}
        except Exception:
            info = {}

        logo_path = info.get("Logo", "")
        if logo_path and os.path.isfile(logo_path):
            logo = "/usr/lib/enigma2/python/Plugins/Extensions/webradioFS/data/logo.png"
            try:
                copyfile(logo_path, logo)
            except Exception:
                logo = None
        return info, logo

    def _handle_command(self, command):
        from .plugin import running

        if command == "starten" and not running:
            run_webradioFS(self)
        elif command == "stoppen":
            from .plugin import abschalt

            abschalt()
        elif command == "box_on" and Screens.Standby.inStandby:
            from .plugin import standby_toggle

            standby_toggle(self)
        elif command == "play_in_standby" and Screens.Standby.inStandby:
            from .plugin import play_in_standby

            play_in_standby(self)

    def action(self, req=None):
        from .plugin import running

        self.check_timer.stop()
        if req is not None:
            req.setHeader("Content-type", "text/html; charset=UTF-8")
            args = req.args or {}
            if b"cmd" in args:
                self._handle_command(args[b"cmd"][0].decode("utf-8", "ignore"))
                self.akt_time = "5"
            elif b"vol0.y" in args:
                self.vol_set("mute")
                self.akt_time = "5"
            elif b"volm.y" in args:
                self.vol_set("minus")
                self.akt_time = "5"
            elif b"volp.y" in args:
                self.vol_set("plus")
                self.akt_time = "5"
            else:
                self.check_timer.startLongTimer(20)

        info, logo = self._read_status()
        station = escape(str(info.get("Station", "") or ""))
        title = escape(str(info.get("akt_txt", "") or ""))
        fav = escape(str(info.get("Fav", "") or ""))
        volume = VolumeControl.instance.volctrl.getVolume()
        muted = VolumeControl.instance.volctrl.isMuted()
        state = _("running") if running else _("stopped")
        standby = _("yes") if Screens.Standby.inStandby else _("no")

        html = [
            "<html>",
            "<head>",
            '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">',
            f'<meta http-equiv="refresh" content="{self.akt_time}">',
            "<title>webradioFS-webinterface</title>",
            "</head>",
            '<body bgcolor="#666666" text="#FFFFFF">',
            '<div style="max-width:700px;margin:0 auto;font-family:sans-serif;">',
            f"<h2>webradioFS Webinterface <small>{escape(str(myversion))}</small></h2>",
            f"<p><b>Status:</b> {state}<br><b>Standby:</b> {standby}<br><b>Volume:</b> {volume}{' (mute)' if muted else ''}</p>",
        ]
        if logo:
            html.append('<p><img src="/webradiofs/data/logo.png" style="max-width:220px;max-height:220px"></p>')
        if station or title or fav:
            html.append("<p>")
            if station:
                html.append(f"<b>Station:</b> {station}<br>")
            if title:
                html.append(f"<b>Title:</b> {title}<br>")
            if fav:
                html.append(f"<b>Favorite:</b> {fav}<br>")
            html.append("</p>")
        html.extend(
            [
                '<form method="GET"><button type="submit" name="cmd" value="starten">start</button> '
                '<button type="submit" name="cmd" value="stoppen">stop</button> '
                '<button type="submit" name="cmd" value="box_on">toggle standby</button> '
                '<button type="submit" name="cmd" value="play_in_standby">play in standby</button></form>',
                '<form method="GET" style="margin-top:1em;">'
                '<button type="submit" name="volm.y" value="1">vol-</button> '
                '<button type="submit" name="vol0.y" value="1">mute</button> '
                '<button type="submit" name="volp.y" value="1">vol+</button></form>',
            ]
        )
        if audiofiles:
            html.append(f"<p><b>Audio path:</b> {escape(str(audiopath))}</p>")
        html.extend(["</div>", "</body>", "</html>"])
        self.akt_time = "20"
        return "\n".join(html)
