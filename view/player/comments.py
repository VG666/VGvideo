# -*- coding: utf-8 -*-
"""右侧评论/弹幕:拉一次数据画成列表,拖动改宽时复用已有弹幕。(从 main.py 的 App 拆出)

原 App.Load_comments

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



class CommentsMixin(object):


    def Load_comments(self,i,frame,id,s,g):#评论页:原 coral 评论区(整域名)已下线,改用数据源的弹幕接口承载,带点赞数
      if g==1:#主线程:只负责画界面(网络请求一律丢到后台线程,避免卡住界面)
          try:
             self.Load_more.destroy()
          except:
            pass
          _list=getattr(self,"_danmu_data",None) or []
          _w=self.winfo_width()
          _pw=int(self.frame_3.winfo_width() or _w//3.4)#面板实际宽:字号/留白/换行全部按它自适应
          _show=_list[:100]#弹幕接口最多 300 条,全量渲染会造上千控件导致滚动卡顿,只展示点赞最高的一批
          _fs=max(10,int(_pw//36))#正文字号(像素)
          _fs_meta=max(8,int(_pw//64))#点赞/时间等小字
          _pad=int(_pw*0.045)#卡片左右留白
          _wrap=max(140,_pw-_pad*2-14)#正文换行宽(预留滚动条与边距)
          _gap=max(4,int(_pw//90))
          for _n,_c in enumerate(_show):
            try:
              _card=tk.Frame(frame,bg="#26262B")
              _card.pack(side="top",fill="x",padx=_pad,pady=(0 if _n==0 else _gap,0))
              _up=int(_c.get("up") or 0)
              _tp=int(_c.get("time") or 0)
              if _up or _tp>0:#元信息行:没有点赞也没有时间就整行不建,免得白占位置把正文挤窄(旧代码固定字符宽把正文挤成 1px)
                _meta=tk.Frame(_card,bg="#26262B")
                _meta.pack(side="top",fill="x",pady=(0,max(2,_gap//2)))
                if _up:
                  _lab=tk.Label(_meta,text="赞 %d"%_up,fg="#FF5945",bg="#26262B",font=("Comic Sans MS",-_fs_meta,"bold"))
                  _lab.pack(side="left")
                  _lab.bind("<MouseWheel>", self.Wheel)
                if _tp>0:
                  _lab=tk.Label(_meta,text="%d:%02d"%(_tp//60,_tp%60),fg="#8A8A93",bg="#26262B",font=("Comic Sans MS",-_fs_meta))#这条弹幕在视频里的时间点
                  _lab.pack(side="left",padx=(max(6,_gap),0))
                  _lab.bind("<MouseWheel>", self.Wheel)
              try:
                _cmt=tk.Label(_card,text=with_surrogates(str(_c.get("content") or "")),wraplength=_wrap,justify="left",anchor="nw",fg="#DBDBDC",bg="#26262B",font=("Microsoft YaHei",-_fs))
              except:
                _cmt=tk.Label(_card,text="特殊字符无法显示",wraplength=_wrap,justify="left",anchor="nw",fg="#DBDBDC",bg="#26262B",font=("Microsoft YaHei",-_fs))
              _cmt.pack(side="top",fill="x")#正文独占整条宽度并左对齐,不再靠右留空
              _cmt.bind("<MouseWheel>", self.Wheel)
              if _n<len(_show)-1:#评论之间加细分隔线,长列表更好扫读
                tk.Frame(frame,bg="#34343D",height=1).pack(side="top",fill="x",padx=_pad,pady=(_gap,0))
            except:
              pass
          if len(_list)>len(_show):
            _more=tk.Label(frame,text="共 %d 条弹幕,已展示点赞最高的 %d 条"%(_list.__len__(),len(_show)),fg="#8A8A93",bg="#26262B",font=("Microsoft YaHei",-_fs_meta))
            _more.pack(side="top",pady=_gap*2)
            _more.bind("<MouseWheel>", self.Wheel)
      else:#子线程:拉弹幕数据,完成后回主线程渲染(Tk 控件只能在主线程操作)
          def _work(_id=id):
            try:
              _data=_qq_danmu(_id)
            except Exception:
              _data=[]
            def _show():
              self._danmu_data=_data
              try:
                if not frame.winfo_exists():#窗口已关/切换走了:直接丢弃,别操作已销毁的控件
                  return
              except Exception:
                return
              if _data:
                self.Load_comments(i,frame,_id,0,1)
              else:
                try:
                  _dpw=int(self.frame_3.winfo_width() or self.winfo_width()//3.4)
                  _tip=tk.Label(frame,text="暂无评论\n该视频没有弹幕数据,或网络异常,可稍后重试",justify="center",bg="#26262B",fg="#8A8A93",font=("Microsoft YaHei",-max(10,int(_dpw//36))),wraplength=max(140,int(_dpw*0.8)))
                  _tip.pack(pady=int(_dpw//16))
                  _tip.bind("<MouseWheel>", self.Wheel)
                except Exception:
                  pass
            try:
              self.after(0,_show)
            except Exception:
              pass
          _th=Thread(target=_work)
          _th.daemon = True
          _th.start()
