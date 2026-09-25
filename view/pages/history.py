# -*- coding: utf-8 -*-
"""观看记录页(从 main.py 拆出)

    history(vgFrame, style)   读取 Recordset/<剧集id>.json,按最近观看时间排序列出,
                              点"继续播放"从记录到的集数/进度接着放。

记录格式的读写统一在 records.py,本模块只负责扫描目录 + 画列表。
"""
import os
import sys
from threading import Thread
from time import strftime, localtime
from tkinter import Canvas, Frame, Label, PhotoImage

import tkinter.ttk as ttk

import model.state as state
from model.paths import _data_path, _download_dir_arg
from model.records import _REC_EXT, _REC_EXTS, _rec_read
from view.widgets import scrollbar
from view.widgets.nav import nav_button
from controller.entry import VGvideo


class history(object):
  def __init__(self,vgFrame,style):
    _prev=nav_button(state.current_page)#原来直接 .configure(),取不到控件时 AttributeError 会把整个历史页构造搞崩(页面一片空白)
    if _prev is not None:
      _prev.configure(bg='#2A2A31',image=PhotoImage(file=''))
    try:
          self.vgFrame=vgFrame
          self.frame=Canvas(self.vgFrame,bg=style,highlightthickness=0)
          self.content=Frame(self.frame,bg=style)
          scrollbar.setup(self.vgFrame)#深色滚动条:必须带 map,只 configure 滑块中间会一直是白的
          x=Frame(self.frame,width=12,highlightthickness=0,bd=0,bg=style)
          x.pack(side="right",fill="y")
          self.scrollbar=ttk.Scrollbar(x,orient="vertical",command=self.frame.yview)
          self.frame.configure(yscrollcommand=self.scrollbar.set)
          self._cw=self.frame.create_window((0,0),window=self.content,anchor='nw')#记住画布项id:画布变宽时要把内容拉到同宽,否则整行只按内容自身宽度取宽,x 轴铺不满
          self.scrollbar.place(x=0, y=-13, relheight=1,height=26,relwidth=1)
          self.frame.place(x=0, y=0,relheight=1,relwidth=1)
          self.frame.bind("<Configure>",lambda _e:self.frame.itemconfigure(self._cw,width=max(1,_e.width-12-_e.width//80)))#减掉右侧 12px 滚动条再留出约 1% 的小空,行尾不会顶到滚动条上
          self.content.bind("<Configure>",lambda event: self.frame.configure(scrollregion=self.frame.bbox("all"),width=self.vgFrame["width"],height=self.vgFrame["height"]))
          self.content.bind("<MouseWheel>", self.Wheel)
          self.frame.bind("<MouseWheel>", self.Wheel)
          self.scrollbar.bind("<MouseWheel>",self.Wheel)
          Search_data=Thread(target=self.history_data)#多线程载入
          Search_data.daemon = True#守护线程
          Search_data.start()#启动
    except Exception as err:
      print("历史页初始化失败:",err)#原来 except 后面直接 pass,出错时页面静默变成空白,看不出原因
  def Wheel(self,event):#鼠标滚轮:与搜索页一致
    try:
      if "win" in sys.platform:
        self.frame.yview_scroll(int(-1*(event.delta/120)),"units")
      else:
        self.frame.yview_scroll(int(-1*event.delta),"units")
      return "break"
    except Exception:
      pass
  def bind_wheel(self,widget):#滚轮事件不会冒泡到父级,整行的子控件都要挨个绑
    try:
      widget.bind("<MouseWheel>",self.Wheel)
      for i in widget.winfo_children():
        self.bind_wheel(i)
    except Exception:
      pass
  def _history_items(self):#扫描观看记录,返回 [[修改时间,剧集id,集索引,播放进度,剧名],...],最近看的排最前
    _out=[]
    _dir=_data_path("Recordset")
    try:
      _names=os.listdir(_dir)
    except Exception:
      return _out
    _done=set()#同一部剧同时存在多种格式的记录文件时,只算新格式 .json 那一条
    for _name in sorted(_names,key=lambda _s:not _s.lower().endswith(_REC_EXT)):
      _low=_name.lower()
      _mid=""
      for _ext in _REC_EXTS:
        if _low.endswith(_ext):
          _mid=_name[:-len(_ext)]
          break
      if not _mid or _mid in _done:
        continue
      _done.add(_mid)
      _p=os.path.join(_dir,_name)
      _r=_rec_read(_mid) or {}
      try:
        _out.append([os.path.getmtime(_p),_mid,max(0,int(_r.get("episode") or 0)),max(0.0,min(1.0,float(_r.get("progress") or 0.0))),str(_r.get("name") or "")])
      except Exception:
        pass
    _out.sort(key=lambda i:i[0],reverse=True)#最近观看的排最上面
    return _out
  def history_data(self):#观看记录列表:Recordset 目录下每部看过的剧一个 <剧集id>.json
    try:
      try:
        _w=int(float(self.vgFrame["width"]))
        _h=int(float(self.vgFrame["height"]))
      except Exception:#还没布局时退回实际尺寸
        _w,_h=self.vgFrame.winfo_width(),self.vgFrame.winfo_height()
      _list=self._history_items()
      Label(self.content,text=f"  最近观看 {len(_list)} 部",bg=state.style,fg="#FF5C38",font=("Comic Sans MS",-1*_w//52,"bold"),anchor='w').pack(fill="x")
      if not _list:
        Label(self.content,text="还没有观看记录:搜索并播放过的剧集会出现在这里",bg=state.style,fg="#DBDBDC",font=("Comic Sans MS",-1*_w//62)).pack(pady=_h//4)
        return
      _row_h=max(56,int(_h//7))
      for _n,(_mtime,_mid,_ep,_pos,_nm) in enumerate(_list,1):
        row=Frame(self.content,bg="#1C1E26",height=_row_h,highlightthickness=0)
        row.pack(fill="x",pady=max(1,_h//100))
        row.pack_propagate(False)
        Label(row,text=f"{_n:02d}",bg="#1C1E26",fg="#4E4E54",font=("Comic Sans MS",-1*_w//62,"bold")).pack(side="left",padx=(_w//70,_w//90))
        box=Frame(row,bg="#1C1E26")
        box.pack(side="left",fill="both",expand=True)
        _seen=f"上次看到第 {_ep+1} 集 · 已看 {int(round(_pos*100))}% · {strftime('%Y-%m-%d %H:%M',localtime(_mtime))}"
        title=Label(box,text=" "+(_nm or _mid),bg="#1C1E26",fg="#FFFFFF",font=("Comic Sans MS",-1*_w//60,"bold"),cursor="hand2",anchor='w')#有剧名就显示剧名,还没有名字就先显示剧集id
        title.pack(fill="x",pady=(_row_h//8,0))
        Label(box,text=(" "+_mid+" · "+_seen) if _nm else (" "+_seen),bg="#1C1E26",fg="#818182",font=("Comic Sans MS",-1*_w//82),anchor='w').pack(fill="x")
        bar=Frame(box,bg="#2A2A31",height=4)#进度条:宽度就是播放进度
        bar.pack(fill="x",padx=(_w//80,_w//40),pady=(_row_h//20,0))
        Frame(bar,bg="#FF5C38",height=4).place(x=0,y=0,relwidth=max(0.0,min(1.0,_pos)),relheight=1)
        play=Label(row,text=" 继续播放 ",bg="#FF5C38",fg="#FFFFFF",font=("Comic Sans MS",-1*_w//64),cursor="hand2")
        play.pack(side="right",padx=(_w//90,_w//60))
        def _open(_mid=_mid):#续播:与搜索页点卡片走同一条路,集数与进度由 Recordset 记录自动接上
          try:
            VGvideo("video.exe 2 "+_mid+" "+_download_dir_arg())#下载目录统一从 config.json 取(带引号)
          except Exception as err:
            print("播放失败:",err)
        title.bind("<Enter>",lambda *e,w=title:w.configure(fg="#FF5C38"))
        title.bind("<Leave>",lambda *e,w=title:w.configure(fg="#FFFFFF"))
        play.bind("<Enter>",lambda *e,w=play:w.configure(bg="#FF7300"))
        play.bind("<Leave>",lambda *e,w=play:w.configure(bg="#FF5C38"))
        for _c in (title,play):
          _c.bind("<Button-1>",lambda *e,f=_open:Thread(target=f).start())
        self.bind_wheel(row)
    except Exception as err:
      print("历史记录加载失败:",err)
