# -*- coding: utf-8 -*-
"""播放器窗口 App —— 只负责"组装"(从 main.py 拆出)。

原来 1179 行的 App 被切成 6 个 mixin,这里按职责顺序继承后拼回同一个类:

    class App(PlaybackMixin, PlayerViewMixin, PanelMixin, ProgressMixin,
              EpisodesMixin, CommentsMixin, Window_chrome, tk.Toplevel)

mixin 都放在 view/player/ 下;查找顺序就是上面这个顺序,方法名互不重复,所以谁先谁后都不影响行为。
"""
import tkinter as tk

import model.state as state
from view.chrome import Window_chrome
from view.player.playback import PlaybackMixin
from view.player.view import PlayerViewMixin
from view.player.panel import PanelMixin
from view.player.progress import ProgressMixin
from view.player.episodes import EpisodesMixin
from view.player.comments import CommentsMixin
import sys
from threading import Thread
from time import sleep
from json import loads

import tkinter as tk
from tkinter import (Frame, Label, Button, Toplevel, Canvas, Menu, PhotoImage,
                     filedialog, END, CENTER)

import tkinter.ttk as ttk
import tkinter.messagebox
from PIL import Image, ImageTk

import model.state as state
from model.paths import application_path, IS_WINDOWS, windll, _data_path
from view.image import Picture_transcoding, _safe_attributes, with_surrogates
from view.chrome import Window_chrome
from model.engine import tkPlayer
from model.records import _rec_read, _rec_save, _rec_album_name
from model.download import _dl_video
from model.api import (_qq_episodes, _qq_ep_title, _qq_danmu, _qq_vip_probe, _qq_video_title,
                  _qq_play_title, _resolve_url, _json_load)
from view.widgets.episode import switch_episode, style_episode_list, attach_episode_hover
from controller.entry import reset_windows_opened, seek_on_arrow

try:                                   # 仅 Windows 有
    import max_win
except Exception:
    max_win = None
try:
    from ctypes import wintypes
except Exception:                      # 非 Windows 下 ctypes.wintypes 不可用
    class wintypes(object):
        pass


class App(PlaybackMixin, PlayerViewMixin, PanelMixin, ProgressMixin, EpisodesMixin, CommentsMixin, Window_chrome, tk.Toplevel):
    def _drag_finished(self):#拖拽结束:若处于全屏则退出全屏(拖拽只可能发生在普通窗口,此判断作为兜底)
        if self.xsv==3 or getattr(self,'xxssxs',None)==8:
            self.click(8)
        self._maxed=False#拖动只会发生在普通窗口(最大化被 _drag_locked 挡掉),这里再把标志/图标对齐,避免残留成"图标是还原态、窗口却已经是普通大小"
        try:
            self.Maximize_normal["text"]="☐"
        except Exception:
            pass
