# -*- coding: utf-8 -*-
"""直播间列表(从 main.py 拆出)

    live_broadcast(vgFrame, style)   顶部按频道名分按钮,下面列出该频道的频道,
                                     点封面/名字直接起播放器。

频道数据在 model.api(live_src):公开播放列表(内置实测清单 / config/live.m3u /
config.json 的 LIVE_M3U),条目里的地址就是播放地址,本模块只负责画界面。
原先的咪咕接口已不可用 —— 它返回的 m3u8 缺 CDN 校验签名,CDN 一律回 HTTP 661,
表现就是"地址能取到、播放器拉不到流"。
"""
import sys
from threading import Thread
from tkinter import Canvas, Frame, LabelFrame, Label, Button, PhotoImage

import tkinter.ttk as ttk
from PIL import ImageTk

import model.state as state
from view.image import Picture_transcoding
from model.api import live_channel_data, live_channel_url, fetch_image
from view.widgets import scrollbar
from view.widgets.nav import nav_button
from controller.entry import VGvideo


class live_broadcast(object):
  def __init__(self,vgFrame,style):
    nav_button(state.current_page).configure(bg='#2A2A31',image=PhotoImage(file=''))
    state.current_page=state.target_page
    state.nav_buttons[6].configure(bg='#131824',image=PhotoImage(file=''))
    self.vgFrame = vgFrame
    state.live_channels={}
    self.data_Label=[]
    try:
      state.live_channels=live_channel_data()#公开源:内置实测清单 / config/live.m3u / config.json 的 LIVE_M3U
      if not state.live_channels:
        raise RuntimeError("没有拿到任何直播频道")
      scrollbar.setup(self.vgFrame)#深色滚动条:必须带 map,只 configure 滑块中间会一直是白的
      self.frame=Canvas(self.vgFrame,bg=style,highlightthickness=0)
      self.content=Frame(self.frame,bg=style)
      x=Frame(self.frame,width=12,highlightthickness=0,bd=0,bg=style)
      x.pack(side="right",fill="y")
      self.scrollbar=ttk.Scrollbar(x,orient="vertical",command=self.frame.yview)
      self.frame.configure(yscrollcommand=self.scrollbar.set)
      self.scrollbar.place(x=0, y=-13, relheight=1,height=26,relwidth=1)
      self.frame.place(rely=1/len(state.live_channels),relheight=1-1/len(state.live_channels),relwidth=1)
      self.frame.create_window((0,0),window=self.content,anchor='nw')
      self.content.bind("<MouseWheel>", self.Wheel)
      self.frame.bind("<MouseWheel>", self.Wheel)
      self.scrollbar.bind("<MouseWheel>",self.Wheel)
      len_i=0
      for i in state.live_channels:
        len_i=len_i+len(i)
      for i in range(len(state.live_channels)):
          self.data_Label.append(Button(self.vgFrame,fg="#FFFFFF",bg="#2A2A31",text=list(state.live_channels)[i],bd=0,command=lambda i=i:self.switch(list(state.live_channels)[i],i,style)))
          len_x=0
          for e in range(i):
            len_x=len_x+len(list(state.live_channels)[e])
          self.data_Label[i].place(relx=len_x/len_i,relheight=1/len(state.live_channels),relwidth=len(list(state.live_channels)[i])/len_i)
      Search_data=Thread(target=self.Search_data,args=(self.content,list(state.live_channels)[0],0,style))#多线程载入
      Search_data.daemon = True#守护线程
      Search_data.start()#启动
      self.content.bind("<Configure>",lambda event: self.frame.configure(scrollregion=self.frame.bbox("all"),width=self.vgFrame["width"],height=self.vgFrame["height"]))
      self.vgFrame.bind("<Configure>",self.vgFrame_configure)
    except Exception as e:
      print("直播频道载入失败:",e)#原来静默 pass,页面只会是一片空白,看不到原因
      Label(self.vgFrame,text="直播源不可用\n请在 config/live.m3u 放一份播放列表,\n或在 config.json 的 vgapi 段 LIVE_M3U 里填订阅地址",
            font=("微软雅黑",-22),fg="#FFFFFF",bg=style,justify="left").place(x=20,y=20)

  def Search_data(self,frame,data_name,i,style):
    for bg in self.data_Label:
      bg["bg"]="#2A2A31"
    self.data_Label[i]["bg"]="#181915"
    for i in range(len(state.live_channels[data_name])):
      try:
        self.scrollbar.place_forget()
      except:
        pass
      if self.scrollbar.get()!=(0.0, 1.0):
        self.scrollbar.place(x=0, y=-13, relheight=1,height=26,relwidth=1)
      try:
        info=state.live_channels[data_name][i]
        url=live_channel_url(info[0])#公开源:条目里的地址就是播放地址,不用再取址
        if not url:
          continue
        if info[3] and "http" in str(info[3]):
          try:
            info[3]=ImageTk.PhotoImage(Picture_transcoding(496,280,496//2,280//2,fetch_image(info[3])))
          except Exception as e:
            print("直播封面加载失败:",e)
            info[3]=None
        if not isinstance(info[3],ImageTk.PhotoImage):
          info[3]=None
        if not info[2]:
          info[2]="暂无节目"
        data=LabelFrame(frame,width=10000,height=280//2,bg=style,borderwidth=0)
        data.pack(fill="x",pady=3)
        #公开源大多没有台标:没封面就别占着左侧那一块,文字从左边缘排,不给空槽
        if info[3] is not None:
          img=Label(data,bg=style,image=info[3],width=496,height=280//2,cursor="hand2")
          img.place(x=-(496-496//2)//2,y=0)
          img.bind("<Button-1>",lambda event,u=url:Thread(target=lambda:VGvideo(f'video.exe 4 {u} ""')).start())
          img.bind("<MouseWheel>",self.Wheel)
          align="ne"
          x_text=(496-496//2)*1.05
        else:
          align="nw"
          x_text=10
        name=Label(data,text=" "+info[1],font=("Comic Sans MS",-30,"bold"),fg="#FF5C38",bg=style,cursor="hand2",anchor=align)
        name.place(x=x_text,y=0)
        name.bind("<Button-1>",lambda event,u=url:Thread(target=lambda:VGvideo(f'video.exe 4 {u} ""')).start())
        brief_introduction=Label(data,text=("       "+info[2]) if info[3] is not None else info[2],font=("Comic Sans MS",-20),fg="#FFFFFF",bg=style,anchor=align)
        brief_introduction.place(x=x_text,y=60)
        name.bind("<MouseWheel>",self.Wheel)
        data.bind("<MouseWheel>",self.Wheel)
        brief_introduction.bind("<MouseWheel>",self.Wheel)
      except Exception as e:
        print("直播频道行绘制失败:",e)

  def Wheel(self,event):#鼠标滚轮动作
        if "win" in sys.platform:#windows系统需要除以120
          platform=int(-1*(event.delta/120))
        else:
          platform=int(-1*event.delta)
        if int(-1*(event.delta/120))==-1:
          if (self.scrollbar.get()[0]!=0):
            self.frame.yview_scroll(platform, "units")
            return "break"
        else:
          self.frame.yview_scroll(platform, "units")
          return "break"  

  def vgFrame_configure(self,event):
    if event.width>event.height:
      for i in self.data_Label:
        i["font"]=('微软雅黑',int(event.height*0.03))
    if event.width<event.height:
      for i in self.data_Label:
        i["font"]=('微软雅黑',int(event.width*0.03))
    else:
      for i in self.data_Label:
        i["font"]=('微软雅黑',int(event.height*0.03))

  def switch(self,name,i,style):
      self.frame.destroy()#删除控件
      self.content.destroy()#删除控件
      self.scrollbar.destroy()#删除控件
      #将所有控件重新创造一次
      self.frame=Canvas(self.vgFrame,bg=style,highlightthickness=0)
      self.content=Frame(self.frame,bg=style)
      x=Frame(self.frame,width=12,highlightthickness=0,bd=0,bg=style)
      x.pack(side="right",fill="y")
      self.scrollbar=ttk.Scrollbar(x,orient="vertical",command=self.frame.yview)
      self.frame.configure(yscrollcommand=self.scrollbar.set)
      self.scrollbar.place(x=0, y=-13, relheight=1,height=26,relwidth=1)
      self.frame.place(rely=1/len(state.live_channels),relheight=1-1/len(state.live_channels),relwidth=1)
      self.frame.create_window((0,0),window=self.content,anchor='nw')
      self.content.bind("<MouseWheel>", self.Wheel)
      self.frame.bind("<MouseWheel>", self.Wheel)
      self.scrollbar.bind("<MouseWheel>",self.Wheel)
      Search_data=Thread(target=self.Search_data,args=(self.content,name,i,style))#多线程载入
      Search_data.daemon = True#守护线程
      Search_data.start()#启动
      self.content.bind("<Configure>",lambda event: self.frame.configure(scrollregion=self.frame.bbox("all"),width=self.vgFrame["width"],height=self.vgFrame["height"]))
