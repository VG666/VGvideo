# -*- coding: utf-8 -*-
"""底部进度条与倍速:定时刷新进度、松开方向键对齐、回退到上次进度。(从 main.py 的 App 拆出)

原 App.Speed_of_progress / Speed_of_progresss / Recover

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



class ProgressMixin(object):


    def Speed_of_progress(self):
        i=0
        x=0
        times=0.0
        try:
          if state.argv[1]=="2":
            # 片名(getinfo)获取失败也要让本线程继续,否则换集/续播监控会停
            try:
                _vid=state.current_url.rsplit("=vg")[0][::-1].rsplit("&")[0][::-1] if "=vg" in str(state.current_url) else ""
                if _vid:
                    _ti=_qq_play_title(_vid)
                    if _ti: self.name["text"]=_ti
            except Exception:
                pass
            self.url=state.current_url
            try:
              style_episode_list(state.current_episode)#统一样式:非当前集浅灰字,当前集橙底高亮(旧代码黑字黑底等于看不见)
            except:
              pass
            try:  # 续播进度(记录固定放程序目录 Recordset,JSON;历史 .ini / .vgini 也认)
                _r=_rec_read(state.argv[2])
                if _r:
                    times=float(_r.get("progress") or 0.0)
                if times:
                    self.s.set(times*10000)
            except Exception:
                pass
        except Exception:
          pass
        while True:
            try:#选集高亮随当前集(vgi)刷新:换集后监控线程常驻,无需重启线程就能更新高亮
                if state.argv[1]=="2" and getattr(self,"_last_hl",None)!=state.current_episode:
                    style_episode_list(state.current_episode)#换集后刷新样式:非当前集浅灰字,当前集橙底高亮
                    self._last_hl=state.current_episode
            except Exception:
                pass
            try:
                if state.argv[1]=="2":
                    # 只有真地址(http)才允许 set_uri:否则会把 cid 当 MRL 送进 VLC
                    if str(state.current_url).startswith("http") and self.url!=state.current_url:
                        try: self.click(1)
                        except Exception: pass
                        try: self.s.set(0)
                        except Exception: pass
                        try:
                            self.player.set_uri(state.current_url)
                            self.player.set_marquee()
                        except Exception: pass
                        try: self.click(0)
                        except Exception: pass
                        # 不退出本监控线程:后续点选集换集时还能继续响应
                    self.url=state.current_url
            except Exception:
                pass
            try:
                if state.nonono:
                    self._close_player()
                    break
            except Exception:
                pass
            try:
                _proceed=((self.player.get_length()!=0 and self.player.get_state()==1) or i==1)
            except Exception:
                _proceed=False
            if _proceed:
                try:
                  while True:
                      if i==1:
                        break
                      if self.player.get_state() == 1:
                        self.player.pause()
                      self.player.set_position(times)
                      if float(str(self.player.get_position())[:len(str(times))-1])==float(str(times)[:len(str(times))-1]):
                        self.player.resume()
                        if self.player.get_state()==1:
                          break
                except:
                  pass
                try:
                    i=1
                    self.player.set_volume(int(self.music.get()))
                    if state.argv[1]=="2":
                        try:  # 观看记录:固定放程序目录 Recordset,写成 JSON(集数/进度/剧名/时间一起刷新)
                            _nm=_rec_album_name(self)#剧名取自已经拿到的剧集信息;取不到就保留记录里原有的名字
                            if self.player.get_state()==-1:
                                _rec_save(state.argv[2],episode=state.current_episode,progress=0.0,name=_nm)
                            else:
                                _rec_save(state.argv[2],episode=state.current_episode,progress=self.player.get_position(),name=_nm)
                        except Exception:
                            pass
                    self.s["to"]=10000
                    self.s.bind("<Button-1>",self.Speed_of_progresss)
                    self.s.bind("<Button-1>",lambda event:self.s.set(event.x/self.s.winfo_width()*10000),"+")
                    self.s.bind("<ButtonRelease-1>",self.Recover)
                    self.progress_bar.bind("<Button-1>",self.Speed_of_progresss)
                    self.progress_bar.bind("<Button-1>",lambda event:self.s.set(event.x/self.s.winfo_width()*10000),"+")
                    self.progress_bar.bind("<B1-Motion>",lambda event:self.s.set(event.x/self.s.winfo_width()*10000))
                    self.progress_bar.bind("<ButtonRelease-1>",self.Recover)
                    get_lengths=self.player.get_length()
                    get_length=get_lengths
                    get_times=self.player.get_time()
                    get_time=get_times
                    if len(str(get_time//1000-get_times//1000//60*60))==2:
                      get_times=f":{get_time//1000-get_time//1000//60*60}"
                    else:
                      get_times=f":0{get_time//1000-get_time//1000//60*60}"
                    if len(str(get_time//1000//60-get_time//1000//60//60*60))==2:
                      get_times=f":{get_time//1000//60-get_time//1000//60//60*60}"+get_times
                    else:
                      get_times=f":0{get_time//1000//60-get_time//1000//60//60*60}"+get_times
                    if len(str((get_time//1000//60//60)))==2:
                      get_times=f"{get_time//1000//60//60}"+get_times
                    else:
                      get_times=f"0{get_time//1000//60//60}"+get_times
                    if len(str(get_length//1000-get_length//1000//60*60))==2:
                      get_lengths=f":{get_length//1000-get_length//1000//60*60}"
                    else:
                      get_lengths=f":0{get_length//1000-get_length//1000//60*60}"
                    if len(str(get_length//1000//60-get_length//1000//60//60*60))==2:
                      get_lengths=f":{get_length//1000//60-get_length//1000//60//60*60}"+get_lengths
                    else:
                      get_lengths=f":0{get_length//1000//60-get_length//1000//60//60*60}"+get_lengths
                    if len(str((get_length//1000//60//60)))==2:
                      get_lengths=f"{get_length//1000//60//60}"+get_lengths
                    else:
                      get_lengths=f"0{get_length//1000//60//60}"+get_lengths
                    if str(get_lengths)[:3]=="00:":
                      self.videotime["text"]=str(get_lengths)[3:]+"/"+str(get_times)[3:]
                    else:
                      if str(get_times)[:3]!="00:":
                        self.videotime["text"]=str(get_lengths)+"/"+str(get_times)
                      else:
                        self.videotime["text"]=str(get_lengths)+"/"+str(get_times)[3:]
                    del get_times,get_time,get_lengths,get_length
                    if self.player.get_state()==1:
                        self.s.set(self.player.get_position()*10000)

                except:
                      pass
                try:
                  pass
                  #print(int(1000 //(self.player.media.get_fps() or 25)))
                except Exception:
                  pass
            try:
                sleep(0.05)
            except Exception:
                pass

    def Speed_of_progresss(self,*event):
        if self.player.get_state() == 1:
            self.player.pause()


    def Recover(self,*event):
      if self.x==1:
        while True:
            self.player.set_position(self.s.get()/10000)
            if float(str(self.player.get_position())[:len(str(self.s.get()/10000))-1])==float(str(self.s.get()/10000)[:len(str(self.s.get()/10000))-1]):
              break
        self.click(0)
      elif self.x==0:
        while True:
            self.player.set_position(self.s.get()/10000)
            if float(str(self.player.get_position())[:len(str(self.s.get()/10000))-1])==float(str(self.s.get()/10000)[:len(str(self.s.get()/10000))-1]):
              break
        self.click(1)
