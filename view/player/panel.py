# -*- coding: utf-8 -*-
"""右侧选集/评论面板的宽度:拖动分隔条、悬浮高亮、跟随窗口缩放还原。(从 main.py 的 App 拆出)

原 App._panel_limits / _panel_width_set / _panel_drag_* / _panel_hover / _panel_on_window

本模块的方法都通过 self 与其它 mixin 协作,合并后与原来的 App 等价。
"""
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
from model.uiprefs import get_float as _ui_pref_get, set_value as _ui_pref_set
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



class PanelMixin(object):


    def _panel_limits(self):#右侧面板宽度上下限:太窄选集按钮连字都放不下,太宽视频画面就剩一条
        _w=max(320,int(self.winfo_width() or 900))
        return max(180,int(_w*0.16)), max(240,int(_w*0.55))


    def _panel_width_set(self,_w,_rebuild=False):#统一改面板宽度:必须关掉几何传播,否则 frame 被子控件顶回内容宽,一松手就弹回去
        try:
            _lo,_hi=self._panel_limits()
            _w=max(_lo,min(_hi,int(_w)))
            try: self.frame_3.pack_propagate(False)
            except Exception: pass
            self.frame_3.configure(width=_w)
            self._panel_w=_w
            self._panel_ratio=_w/float(max(320,int(self.winfo_width() or 1)))
            try:#片名跟着面板宽换行,面板收窄时才不会把标题截断
                self.name.configure(width=0,wraplength=max(80,_w-int(_w*0.08)))
            except Exception: pass
            if _rebuild:
                try: self.frame_3.update_idletasks()#先让布局生效,下面 Anthology 量到的才是新宽度
                except Exception: pass
                try:
                    self._reuse_danmu=True#评论页用缓存重画,避免拖一下就重新拉一次弹幕
                    self.Anthology(self.frame_3,self.Anthologyggg)#按新宽度重算字号/列数/换行
                except Exception: pass
                finally:
                    self._reuse_danmu=False
        except Exception:
            pass


    def _panel_drag_start(self,event):#按下分隔条:量出当前宽度并锁定,之后才拖得动
        try:
            if not self._panel_w:
                _pw=int(self.frame_3.winfo_width() or 0)
                self._panel_w=_pw if _pw>1 else int(self.winfo_width()//3.4)#窗口还没量出宽度时退回默认比例,别让面板一下缩到最小
            try: self.frame_3.pack_propagate(False)
            except Exception: pass
            self.frame_3.configure(width=self._panel_w)
            self._pdrag_x=int(event.x_root)
            self._pdrag_w=self._panel_w
            self._panel_hover(True)
        except Exception:
            self._pdrag_x=None


    def _panel_drag_move(self,event):#拖动中:面板贴右边,鼠标往左拖变宽往右拖变窄;先只改宽度不重建列表(重建控件多,拖起来会卡)
        if self._pdrag_x is None:
            return
        try:
            self._panel_width_set(self._pdrag_w-(int(event.x_root)-self._pdrag_x))
        except Exception:
            pass


    def _panel_drag_end(self,event=None):#松手:按新宽度重建一次当前标签页,选集字号/列数/评论换行全部重新适配
        if self._pdrag_x is None:
            return
        self._pdrag_x=None
        try:#松手后鼠标可能还停在分隔条上,这时保持高亮,免得看起来没反应
            _px,_py=self.winfo_pointerxy()
            _over=self.grip.winfo_rootx()<=_px<=self.grip.winfo_rootx()+self.grip.winfo_width()
        except Exception:
            _over=False
        self._panel_hover(_over)
        self._panel_width_set(self._panel_w,True)
        self._panel_save()#松手即记忆:下次打开播放器,分栏还停在这次拖出来的位置


    def _panel_restore(self):#分栏位置记忆:启动时按上次拖出来的比例摆好右侧面板;没记过就保持默认宽度
        try:
            _r=_ui_pref_get("player","panel_ratio")
            if _r is None:
                return
            _r=float(_r)
            if not 0.05<_r<0.95:#手改坏或换过显示器时,别把面板摆成一条缝或铺满整屏,直接当没记过
                return
            _w=int(self.winfo_width() or 0)
            if _w<=1:#窗口还没量出宽度,这次不摆,后面的 <Configure> 会按比例补上
                return
            self._panel_width_set(int(_w*_r))
        except Exception:
            pass


    def _panel_save(self):#把当前分栏位置记到 uiprefs.json(和窗口宽度的比例,换分辨率/最大化都对得上)
        try:
            if self._panel_ratio:
                _ui_pref_set("player","panel_ratio",round(float(self._panel_ratio),4))
        except Exception:
            pass


    def _panel_hover(self,_on):#分隔条悬停/拖动时高亮
        try:
            self.grip.configure(bg="#FF5C38" if _on else "#3D3F44")
        except Exception:
            pass


    def _panel_on_window(self,event=None):#窗口整体变大变小(最大化/还原/拉伸)时,面板宽度按用户拖出的比例跟着走;没拖过就不干预,保持原来的自适应
        try:
            if not self._panel_ratio or self._pdrag_x is not None:
                return
            _w=int(self.winfo_width() or 0)
            if _w<=1 or _w==self._panel_last_ww:#<Configure> 会被子控件冒泡触发很多次,宽度没变就直接返回
                return
            self._panel_last_ww=_w
            self._panel_width_set(int(_w*self._panel_ratio))
        except Exception:
            pass
