# -*- coding: utf-8 -*-
"""右侧选集表:宫格或单列布局、当前集高亮、滚轮翻页。(从 main.py 的 App 拆出)

原 App.Anthology / Wheel

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
                  _qq_play_title, _resolve_url, play_fail_msg, _json_load)
from view.widgets.episode import switch_episode, style_episode_list, attach_episode_hover
from view.widgets import scrollbar
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



class EpisodesMixin(object):


    def Anthology(self,win,i):
      self.Anthologyggg=i
      if i==1:
        try:
           self.myframe.destroy()
        except:
          pass
        self.Anthologys["bg"]="#26262B"
        self.comment["bg"]="#181915"
        if not self.html:#选集信息还没拿到:提示并保持窗口可用,不解析空串
            try:
                tk.Label(self.frame_3,text="选集信息获取失败\n请检查网络后,再点一次[选集]重试",bg="#26262B",fg="#DBDBDC",wraplength=int(self.winfo_width()//3.5)).pack(pady=10)
            except Exception:
                pass
            return
        try:
            html=loads(self.html[13:-1] if self.html.startswith("QZOutputJson") else self.html)["PlaylistItem"]
        except Exception:
            html=None
        if not html or not isinstance(html,dict) or "videoPlayList" not in html:
          self.frame_3.pack_forget()#数据异常(未收录/需VIP等):播放器本体照常可用
          html=[{}]
          try:
            html[0]["id"]=_qq_vip_probe() or (self._current_ep_id() or "")
          except Exception:
            html[0]["id"]=self._current_ep_id() or ""
          if not html[0].get("id"):
              return
          try:
            _vu=_resolve_url(html[0]["id"])
            if _vu:
                state.current_url=_vu+"&"+html[0]["id"]+"=vg"
                self.loadsi=1
            else:
                self._play_fail_hint(play_fail_msg())#未收录/需VIP 又取不到地址:如实说明原因(加密/权益/网络)
          except Exception:
            pass
          return
        else:
          html=html["videoPlayList"]
          if not isinstance(html,list) or not html:
              return
          for _ep in html:#字段兜底:保证下面构建列表时直接取字段不会炸
              if not isinstance(_ep.get("markLabelList"),list):
                  _ep["markLabelList"]=[]
              if not isinstance(_ep.get("episode_number"),str):
                  _ep["episode_number"]=str(html.index(_ep)+1)
          try:
            if html[0]["id"] in html[0].get("playUrl",""):
              self.p=False
              for i in range(len(html)):
                if "vid" in html[i].get("playUrl",""):
                  html[i]["id"]=html[i]["playUrl"].rsplit("vid=")[1]
                else:
                  try: html[i]["id"]=html[i]["playUrl"][::-1][5:].rsplit("/")[0][::-1]
                  except Exception: html[i]["id"]=html[i].get("id","")
                  self.p=True
            else:
              self.p=False
          except Exception:
            self.p=False
          _epi=max(0,min(len(html)-1,state.current_episode))#当前集索引越界保护
          try:
            if self.loadsi==0:
              _vu=_resolve_url(html[_epi].get("id",""))
              if _vu:
                state.current_url=_vu+"&"+html[_epi]["id"]+"=vg"
                self.loadsi=1
              else:
                self._play_fail_hint(play_fail_msg())#取不到地址:说明原因,别只留个空白播放器
            # 解析失败:不给假地址,url保持原样,交给自动开播/换集兜底或等用户重试
          except Exception:
            pass
          state.episode_buttons=[]
          self.myframe=tk.Frame(self.frame_3,bg="#26262B",relief=tk.GROOVE,bd=0,highlightthickness=0)
          self.myframe.pack(fill="both", expand=tk.YES)#横向也要填满:只填 y 时画布按内容取宽,右侧留空
          scrollbar.setup(self)#深色滚动条:必须带 map,只 configure 滑块中间会一直是白的
          self.canvase=tk.Canvas(self.myframe,bg="#26262B",highlightthickness=0)
          frame=tk.Frame(self.canvase,bg="#26262B",highlightthickness=0)
          x=tk.Frame(self.myframe,width=10,highlightthickness=0,bg="#26262B")
          x.pack(side="right",fill="y")
          self.myscrollbar=ttk.Scrollbar(x,orient="vertical",command=self.canvase.yview)
          self.canvase.configure(yscrollcommand=self.myscrollbar.set)
          self.myscrollbar.place(x=0, y=-13, relheight=1,height=26,relwidth=1)
          self._cw=self.canvase.create_window((0,0),window=frame,anchor='nw')
          self.canvase.pack(side="top",fill="both",expand=tk.YES)#画布横向铺满,否则只占内容宽度
          frame.bind("<MouseWheel>", self.Wheel)
          self.myscrollbar.bind("<MouseWheel>", self.Wheel)
          self.canvase.bind("<MouseWheel>",self.Wheel)
          self.canvase.bind("<Configure>",lambda _e:self.canvase.itemconfigure(self._cw,width=_e.width))#画布变宽时把内层 frame 拉到同宽,子控件才真正铺满 x
          frame.bind("<Configure>",lambda *Event:self.canvase.configure(scrollregion=self.canvase.bbox("all"),width=int(self.winfo_width()//3.5),height=self.winfo_height()))
          if self.xxssxs!=8:
            if self.p:
              for i in range(len(html)):
                if len(html[i]["markLabelList"])>0:
                  if "primeText" in html[i]["markLabelList"][0]:
                    if html[i]["markLabelList"][0]["primeText"]!="预告":
                      state.episode_buttons.append(tk.Button(frame,text=html[i]["episode_number"],width=self.frame_3["width"]//100,font=("Comic Sans MS",-1*self.frame_3["width"]//12,"bold"),bg="#26262B",bd=0, cursor="hand2"))
                      state.episode_buttons[i].grid(row=i//4,column=(i-(i//4*4)),padx=self.frame_3["width"]//33,pady=self.frame_3["width"]//33)
                      state.episode_buttons[i].bind("<MouseWheel>", self.Wheel)
                      state.episode_buttons[i].bind('<Button-1>',lambda *event,_id=html[i]["id"],_i=i:switch_episode(_id,_i))
                      attach_episode_hover(state.episode_buttons[i])
                    else:
                      state.episode_buttons.append(tk.Button(frame,text="预告",width=self.frame_3["width"]//100,font=("Comic Sans MS",-1*self.frame_3["width"]//12,"bold"),bg="#26262B",bd=0, cursor="hand2"))
                      state.episode_buttons[i].grid(row=i//4,column=(i-(i//4*4)),padx=self.frame_3["width"]//33,pady=self.frame_3["width"]//33)
                      state.episode_buttons[i].bind("<MouseWheel>", self.Wheel)
                      state.episode_buttons[i].bind('<Button-1>',lambda *event,_id=html[i]["id"],_i=i:switch_episode(_id,_i))
                      attach_episode_hover(state.episode_buttons[i])     
                  else:
                      state.episode_buttons.append(tk.Button(frame,text=html[i]["episode_number"],width=self.frame_3["width"]//100,font=("Comic Sans MS",-1*self.frame_3["width"]//12,"bold"),bg="#26262B",bd=0, cursor="hand2"))
                      state.episode_buttons[i].grid(row=i//4,column=(i-(i//4*4)),padx=self.frame_3["width"]//33,pady=self.frame_3["width"]//33)
                      state.episode_buttons[i].bind("<MouseWheel>", self.Wheel)
                      state.episode_buttons[i].bind('<Button-1>',lambda *event,_id=html[i]["id"],_i=i:switch_episode(_id,_i))
                      attach_episode_hover(state.episode_buttons[i])
                else:
                      state.episode_buttons.append(tk.Button(frame,text=html[i]["episode_number"],width=self.frame_3["width"]//100,font=("Comic Sans MS",-1*self.frame_3["width"]//12,"bold"),bg="#26262B",bd=0, cursor="hand2"))
                      state.episode_buttons[i].grid(row=i//4,column=(i-(i//4*4)),padx=self.frame_3["width"]//33,pady=self.frame_3["width"]//33)
                      state.episode_buttons[i].bind("<MouseWheel>", self.Wheel)
                      state.episode_buttons[i].bind('<Button-1>',lambda *event,_id=html[i]["id"],_i=i:switch_episode(_id,_i))
                      attach_episode_hover(state.episode_buttons[i])
            else:
              for i in range(len(html)):
                if len(html[i]["markLabelList"])>0:
                  if "primeText" in html[i]["markLabelList"][0]:
                    if html[i]["markLabelList"][0]["primeText"]!="预告":
                      state.episode_buttons.append(tk.Button(frame,text=html[i]["episode_number"],width=self.frame_3["width"],font=("Comic Sans MS",-1*self.frame_3["width"]//12,"bold"),bg="#26262B",bd=0, cursor="hand2"))
                      state.episode_buttons[i].grid(row=i,column=1,padx=self.frame_3["width"]//33,pady=self.frame_3["width"]//33)
                      state.episode_buttons[i].bind("<MouseWheel>", self.Wheel)
                      state.episode_buttons[i].bind('<Button-1>',lambda *event,_id=html[i]["id"],_i=i:switch_episode(_id,_i))
                      attach_episode_hover(state.episode_buttons[i])
                    else:
                      state.episode_buttons.append(tk.Button(frame,text=html[i]["episode_number"],width=self.frame_3["width"],font=("Comic Sans MS",-1*self.frame_3["width"]//12,"bold"),bg="#26262B",bd=0, cursor="hand2"))
                      state.episode_buttons[i].grid(row=i,column=1,padx=self.frame_3["width"]//33,pady=self.frame_3["width"]//33)
                      state.episode_buttons[i].bind("<MouseWheel>", self.Wheel)
                      state.episode_buttons[i].bind('<Button-1>',lambda *event,_id=html[i]["id"],_i=i:switch_episode(_id,_i))
                      attach_episode_hover(state.episode_buttons[i])
                  else:
                      state.episode_buttons.append(tk.Button(frame,text=html[i]["episode_number"],width=self.frame_3["width"],font=("Comic Sans MS",-1*self.frame_3["width"]//12,"bold"),bg="#26262B",bd=0, cursor="hand2"))
                      state.episode_buttons[i].grid(row=i,column=1,padx=self.frame_3["width"]//33,pady=self.frame_3["width"]//33)
                      state.episode_buttons[i].bind("<MouseWheel>", self.Wheel)
                      state.episode_buttons[i].bind('<Button-1>',lambda *event,_id=html[i]["id"],_i=i:switch_episode(_id,_i))
                      attach_episode_hover(state.episode_buttons[i])
                else:
                      state.episode_buttons.append(tk.Button(frame,text=html[i]["episode_number"],width=self.frame_3["width"],font=("Comic Sans MS",-1*self.frame_3["width"]//12,"bold"),bg="#26262B",bd=0, cursor="hand2"))
                      state.episode_buttons[i].grid(row=i,column=1,padx=self.frame_3["width"]//33,pady=self.frame_3["width"]//33)
                      state.episode_buttons[i].bind("<MouseWheel>", self.Wheel)
                      state.episode_buttons[i].bind('<Button-1>',lambda *event,_id=html[i]["id"],_i=i:switch_episode(_id,_i))
                      attach_episode_hover(state.episode_buttons[i])
          else:
            if self.p:
              for i in range(len(html)):
                  state.episode_buttons.append(tk.Button(frame,text=html[i]["episode_number"],width=self.frame_3["width"]//100,font=("Comic Sans MS",-1*self.frame_3["width"]//12,"bold"),bg="#26262B",bd=0))
                  state.episode_buttons[i].grid(row=i//4,column=(i-(i//4*4)),padx=self.frame_3["width"]//15,pady=self.frame_3["width"]//15)
                  state.episode_buttons[i].bind("<MouseWheel>", self.Wheel)
                  state.episode_buttons[i].bind('<Button-1>',lambda *event,_id=html[i]["id"],_i=i:switch_episode(_id,_i))
                  attach_episode_hover(state.episode_buttons[i])
            else:
              for i in range(len(html)):
                  state.episode_buttons.append(tk.Button(frame,text=html[i]["episode_number"],width=self.frame_3["width"],font=("Comic Sans MS",-1*self.frame_3["width"]//12,"bold"),bg="#26262B",bd=0))
                  state.episode_buttons[i].grid(row=i,column=1,padx=self.frame_3["width"]//15,pady=self.frame_3["width"]//15)
                  state.episode_buttons[i].bind("<MouseWheel>", self.Wheel)
                  state.episode_buttons[i].bind('<Button-1>',lambda *event,_id=html[i]["id"],_i=i:switch_episode(_id,_i))
                  attach_episode_hover(state.episode_buttons[i])
          #统一收口选集按钮:旧代码用"面板宽//12"当字号(1920屏上高达47px),比单元格还宽 → 集号被裁掉一半、右侧列被挤出面板
          try:
            _pw=int(self.frame_3.winfo_width() or 0) or int(self.winfo_width()//3.5) or 548#面板真实宽(拿不到时按 1/3.5 兜底)
            _labels=[str(_b.cget("text")) for _b in state.episode_buttons] or [""]
            _cols=4 if self.p else 1#宫格还是单列
            _px=max(2,int(_pw//90))#单元格间距
            def _cellof(_n):
              return max(24,int(_pw/_n-2*_px))#单格可用宽
            def _fit(_n):
              try:#用字体量宽反推字号:按钮自然宽≈文字宽+0.9×字号(实测),负值字号=像素,和按钮 font 口径一致
                from tkinter.font import Font as _Font
                _fnt=_Font(family="Comic Sans MS",size=-20,weight="bold")
                _m=max(_fnt.measure(_t) for _t in _labels)/20.0
              except Exception:
                _m=0.62
              return max(8,min(28,int(_cellof(_n)/(_m+0.9))))
            _fs=_fit(_cols)
            if _cols==4 and _fs<=11:#4 列连 11px 都塞不下(集号偏长):降到 2 列,宁可少列也要把内容显示全
              _cols=2; _px=max(3,int(_pw//70)); _fs=_fit(2)
            for _c in (range(_cols) if _cols>1 else (1,)):
              frame.grid_columnconfigure(_c,weight=1,uniform="epi" if _cols>1 else "")
            for _k,_b in enumerate(state.episode_buttons):
              _b.configure(width=0,font=("Comic Sans MS",-_fs,"bold"))#字号统一按最窄的那一格算,保证每个集号完整可见
              _b.grid_configure(row=_k//_cols,column=(_k%_cols) if _cols>1 else 1,
                                padx=_px,pady=max(2,int(_px*0.7)),sticky="ew")
          except:
            pass
          style_episode_list(state.current_episode)#统一上色:当前集橙底高亮、预告灰字、其余浅灰字
          try:
            self.myscrollbar.place_forget()
          except:
            pass
          self.myscrollbar.update()
          if self.myscrollbar.get()!=(0.0, 1.0):
            self.myscrollbar.place(x=0, y=-13, relheight=1,height=26,relwidth=1)
      elif i==2:
        self.comment["bg"]="#26262B"
        self.Anthologys["bg"]="#181915"
        self.myframe.destroy()
        self.myframe=tk.Frame(self.frame_3,bg="#26262B",relief=tk.GROOVE,bd=0,highlightthickness=0)
        self.myframe.pack(fill="both", expand=tk.YES)#横向也要填满:只填 y 时画布按内容取宽,右侧留空
        scrollbar.setup(self)#深色滚动条:必须带 map,只 configure 滑块中间会一直是白的
        self.canvase=tk.Canvas(self.myframe,bg="#26262B",highlightthickness=0)
        frame=tk.Frame(self.canvase,bg="#26262B",highlightthickness=0)
        x=tk.Frame(self.myframe,width=10,highlightthickness=0,bg="#26262B")
        x.pack(side="right",fill="y")
        self.myscrollbar=ttk.Scrollbar(x,orient="vertical",command=self.canvase.yview)
        self.canvase.configure(yscrollcommand=self.myscrollbar.set)
        self.myscrollbar.place(x=0, y=-13, relheight=1,height=26,relwidth=1)
        self._cw=self.canvase.create_window((0,0),window=frame,anchor='nw')
        self.canvase.pack(side="top",fill="both",expand=tk.YES)#画布横向铺满,否则只占内容宽度
        frame.bind("<MouseWheel>", self.Wheel)
        self.myscrollbar.bind("<MouseWheel>", self.Wheel)
        self.canvase.bind("<MouseWheel>",self.Wheel)
        self.canvase.bind("<Configure>",lambda _e:self.canvase.itemconfigure(self._cw,width=_e.width))#画布变宽时把内层 frame 拉到同宽,子控件才真正铺满 x
        frame.bind("<Configure>",lambda *Event:self.canvase.configure(scrollregion=self.canvase.bbox("all"),width=int(self.winfo_width()//3.5),height=self.winfo_height()))
        state.episode_posters=[]
        id=state.current_url.rsplit("=vg")[0][::-1].rsplit("&")[0][::-1]
        if getattr(self,"_reuse_danmu",False) and getattr(self,"_danmu_data",None):
          self.Load_comments(i,frame,id,0,1)#拖动改宽后的重建:用手里的弹幕缓存直接重画,不再重新请求一遍
        else:
          self.Load_comments(i,frame,id,0,2)


    def Wheel(self,event):#鼠标滚轮动作
        if "win" in sys.platform:#windows系统需要除以120
          platform=int(-1*(event.delta/120))
        else:
          platform=int(-1*event.delta)
        if int(-1*(event.delta/120))==-1:
          if (self.myscrollbar.get()[0]!=0):
            self.canvase.yview_scroll(platform, "units")
            return "break"
        else:
          self.canvase.yview_scroll(platform, "units")
          return "break"  
