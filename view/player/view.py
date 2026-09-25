# -*- coding: utf-8 -*-
"""播放画面与窗口:画布、底部控制条、全屏进出、窗口摆放、缩放键、点击菜单。(从 main.py 的 App 拆出)

原 App.create_video_view / zoomednormal / click / _enter_fullscreen /
_full_screen_geo / _place_window / _resync_video_window / _exit_fullscreen

本模块的方法都通过 self 与其它 mixin 协作,合并后与原来的 App 等价。
"""
import sys
from threading import Thread
from time import sleep, strftime
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
from view.icons import App_icon
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



class PlayerViewMixin(object):


    def create_video_view(self):
        self.Set_thes=1
        # mode 2 的 argv[2] 是剧集 cid,不是播放地址;真正的地址由 _load_play_info 后台解析后写入。
        # 若这里先把 cid 填进 url,启动时的 click(0)/监控线程就会把它当本地文件名丢给 VLC(必然打不开)。
        state.current_url=state.argv[2] if str(state.argv[1])!="2" else ""
        font=self.winfo_height()//35*-1
        self.wh1=self.winfo_width()
        self.wh2=self.winfo_height()
        self.new_x=self.winfo_x()
        self.new_y=self.winfo_y()
        state.style="#303038"
        App_icon.apply(self)#设置标题栏/任务栏图标(win补大图标让任务栏认账,mac/linux用iconphoto)
        self.xxsxs=tk.Frame(self,height=2,bg=state.style)
        self.xxsxs.bind("<Button-1>",self.mobile_2)#绑定移动函数
        self.xxsxs.bind("<B1-Motion>",self.mobile_1)#绑定移动函数
        self.xxsxs.bind("<ButtonRelease-1>",self.mobile_3)#绑定移动函数
        self.xxsxs.pack(side='top',fill="x")
        self.control=tk.Frame(self.xxsxs,bg=state.style)#创建一个容器，在利用表格布局，使得菜单缩小删除三个按钮平行
        self.control.pack(side=tk.RIGHT, padx=10)
        self.bind('<Map>',lambda *minimizevg:self.Set_the(1))#显示主窗口,因为点击一下其实会触发很多次，所以才需要有一个判断
        no=tk.Label(self.control, text='×',fg="#FFFFFF",bg=state.style,font=("PMingLiU-ExtB",int(self.winfo_width()//36*-1)), cursor="hand2")#设置删除按钮使用标签输入文字实现所以把背景调成当前颜色背景字体调整#FFFFFF
        no.grid(row=1, column=2, padx=5)
        no.bind("<Button-1>",lambda *no: self.click(9))#关掉线程关闭
        no.bind("<Button-1>",lambda *no:reset_windows_opened(),"+")#关闭窗口destroy代表关闭
        no.bind("<Button-1>",lambda *no: self._close_player(),"+")#释放视频(走幂等释放,监控线程已释放过也不会再报错)
        no.bind("<Button-1>",lambda *no: self.no.destroy(),"+")#关闭窗口destroy代表关闭
        no.bind("<Leave>",lambda *novg:no.configure(fg="#FFFFFF"))#离开时候变回
        no.bind("<Enter>",lambda *novg:no.configure(fg="#FF5C38"))#进入时变色
        self.Maximize_normal=tk.Label(self.control, text='☐',bg=state.style,fg="#FFFFFF",font=("Comic Sans MS",int(self.winfo_width()//48)*-1), cursor="hand2")#标题栏☐:普通窗口最大化/还原(与主窗口同一套逻辑,不走全屏)
        self.Maximize_normal.grid(row=1, column=1, padx=5)
        self.Maximize_normal.bind("<Button-1>",self.zoomednormal)
        self.Maximize_normal.bind("<Leave>",lambda *Maximizevg:self.Maximize_normal.configure(fg="#FFFFFF"))#离开时候变回
        self.Maximize_normal.bind("<Enter>",lambda *Maximizevg:self.Maximize_normal.configure(fg="#FF5C38"))#进入时变色
        minimize=tk.Label(self.control, text='—',bg=state.style,fg="#FFFFFF",font=("Comic Sans MS",int(self.winfo_width()//48)*-1), cursor="hand2")#设置最小化按钮使用标签输入文字实现所以把背景调成当前颜色背景字体调整#FFFFFF
        minimize.grid(row=1, column=0, padx=5)
        minimize.bind("<Button-1>",lambda *minimizevg: self.minimize_click())#最小化到任务栏(win走无边框还原技巧,mac/linux交给系统)
        minimize.bind("<Leave>",lambda *minimizevg:minimize.configure(fg="#FFFFFF"))#离开时候变回
        minimize.bind("<Enter>",lambda *minimizevg:minimize.configure(fg="#FF5C38"))#进入时变色
        self.frame = tk.Frame(self,bg="#2E2E36")
        self.frame_2=tk.Frame(self.frame,bg="#2E2E36")
        self.frame_3=tk.Frame(self,bg="#26262B",width=int(self.winfo_width()//3.4))
        if state.argv[1]=="2":
            VGfiles=state.argv[3]
            self.frame_3.pack(side=tk.RIGHT,fill="y")
            # 分隔条:面板贴右边,鼠标按住这条竖线左右拖就能改面板宽度,视频画面自动跟着变宽变窄
            self.grip=tk.Frame(self.frame_3,bg="#3D3F44",width=6,cursor="sb_h_double_arrow",bd=0,highlightthickness=0)
            self.grip.pack(side="left",fill="y")#side=left 先pack:它占最左边一条,标题/标签页/列表都排在它右边
            self.grip.bind("<Button-1>",self._panel_drag_start)
            self.grip.bind("<B1-Motion>",self._panel_drag_move)
            self.grip.bind("<ButtonRelease-1>",self._panel_drag_end)
            self.grip.bind("<Enter>",lambda *event:self._panel_hover(True))#悬停变色:让用户看得见这里可以拖
            self.grip.bind("<Leave>",lambda *event:self._panel_hover(self._pdrag_x is not None))
            self.grip.bind("<MouseWheel>",self.click)#滚动调整音量
            self.bind("<Configure>",self._panel_on_window,add="+")#窗口放大/还原时,面板按用户拖出的比例跟着走
            # 片名先显示占位,选集信息后台拉取成功后(_apply_play_info)再换成真实片名;信息获取失败也不影响窗口打开
            self.name=tk.Label(self.frame_3,text="正在获取信息…",font=("Comic Sans MS",-1*int(((self.winfo_screenwidth()-self.winfo_screenwidth()//4)//46)*35.5)//28,"bold"),fg="#FF4F4A",bg="#26262B",wraplength=int(self.winfo_width()//3.5),width=self.winfo_width()//54)
            self.name.pack()
            frames=Frame(self.frame_3,height=self.winfo_width()//40)
            frames.pack(fill="x")
            self.Anthologys=tk.Button(frames,text="选集",bg="#26262B",fg="#FFFFFF",command=lambda *event:self._tab_click(1),bd=1)
            self.Anthologys.place(relx=-0.00189,relwidth=0.5089,relheight=1.1)
            self.comment=tk.Button(frames,text="评论",bg="#26262B",fg="#FFFFFF",command=lambda *event:self._tab_click(2),bd=1)
            self.comment.place(relx=0.50189,relwidth=0.50189,relheight=1.1)
            self._panel_restore()#分栏位置记忆:按上次拖出来的比例摆好右侧面板(见 view/player/panel.py)
        elif state.argv[1]=="3":
          VGfiles=state.argv[3]
        self.frame_2.pack(side='bottom',fill="x")
        if state.argv[1]!="4":
          self.Pause_start=tk.Button(self.frame_2, text=" ▶ ",width=3,height=1,font=("Comic Sans MS",font),bd=0,bg="#2E2E36",cursor="hand2")
          self.Pause_start.pack(side=tk.LEFT, padx=10)
          self.Pause_start.bind("<Button-1>",lambda *event:self.click(self.x))
          self.Pause_start.bind("<MouseWheel>",self.click)#滚动调整音量
        self.Maximize=tk.Button(self.frame_2, text="☐",width=3,height=1,font=("Comic Sans MS",font,"bold"),bg="#2E2E36",bd=0,cursor="hand2")
        self.Maximize.pack(side=tk.RIGHT, padx=10)
        self.Maximize.bind("<Button-1>",lambda *event:self.click(self.xsv))
        self.Maximize.bind("<Button-1>",lambda *event:self._canvas.configure(height=self.winfo_width()),"+")
        self.Maximize.bind("<MouseWheel>",self.click)#滚动调整音量
        if state.argv[1]!=1 and state.argv[1]!="4":
          def _download_current():#下载当前视频:地址取正在播放的链接,aria2 搬字节,ffmpeg 合成为 mp4
            if getattr(self,"_dl_busy",False):#防止连点造成多份下载
              return
            self._dl_busy=True
            _vid=state.current_url.rsplit("=vg")[0][::-1].rsplit("&")[0][::-1] if "=vg" in str(state.current_url) else ""
            # 正在播的往往是解析后的 m3u8 直链,里面没有 vg= 参数:此时上面取出来的会是"整条播放地址",
            # 拿它当 vid 去查片名必然查不到,退化成用整条 URL 命名文件(会顶爆 Windows 路径上限,下载直接失败),
            # 所以这里照 progress.py 的写法先判断有没有 vg=,没有就不当 vid 用。
            try: _title=str(_qq_video_title(_vid) or "").strip()
            except Exception: _title=""
            if not _title:
              try: _title=str(self.name["text"] or "").strip()#退一步用右侧面板显示的片名
              except Exception: _title=""
            if not _title or _title=="正在获取信息…":
              _title="视频_"+strftime("%Y%m%d_%H%M%S")#都没有就按时间命名,绝不拿播放地址当文件名
            _cover=('http://puui.qpic.cn/qqvideo_ori/0/%s_360_204/0'%_vid) if _vid else None#没有 vid 就没有能用的封面直链
            _dl_url=state.current_url#点下按钮这一刻的播放地址(换集后自动跟着变)
            def _set(t):
              try: self.after(0,lambda: de.configure(text=t))
              except Exception: pass
            def _work():
              try:
                # 第 5 个参数(on_msg)故意不传:下载进度的文案又多又长(取播放清单/下载分片 0/123/合并 mp4…),
                # 之前把它接到按钮上,按钮文字被反复撑开、看着一长串,这里只让按钮保持"..."。
                _ok,_msg=_dl_video(_dl_url,VGfiles,_title,_cover)
              except Exception as _e:
                _ok,_msg=False,str(_e)
              _set("⇓")#下载结束(成功或失败)都恢复成原来的下载图标;失败另有弹窗说明
              if not _ok:
                try: self.after(0,lambda: tkinter.messagebox.showwarning("下载失败",str(_msg)))
                except Exception: pass
              self._dl_busy=False
            _set("...")#点下按钮立刻变三个点,整个下载过程保持;结束时由上面 _work 恢复
            _th_dl=Thread(target=_work)
            _th_dl.daemon = True
            _th_dl.start()
          de=tk.Button(self.frame_2,text="⇓",width=3,height=1,font=("Comic Sans MS",font,"bold"),bg="#2E2E36",bd=0,cursor="hand2",command=lambda *event:_download_current())
          de.pack(side=tk.RIGHT, padx=5)
          de.bind("<MouseWheel>",self.click)#滚动调整音量
        if state.argv[1]!="4":
          self.Multiple=tk.Button(self.frame_2,text="倍数:正常",bd=0,bg="#2E2E36",cursor="hand2",command=lambda *event:self.click(6))
          self.Multiple.pack(side=tk.RIGHT, padx=5)
          self.Multiple.bind("<MouseWheel>",self.click)#滚动调整音量
        self.frame.pack(side='bottom',fill="x")
        self._canvas = tk.Canvas(self, bg="black",height=self.winfo_height(),bd=0,highlightthickness=0)
        self._canvas.pack(fill="both",expand=tk.YES)
        self._canvas.bind("<MouseWheel>",self.click)#滚动调整音量
        if state.argv[1]!="4":
          self.s = tk.Scale(self.frame,from_=0,to=10000,bg="#282923",fg='#FF5C38',orient=tk.HORIZONTAL,bd=0,showvalue=0,tickinterval=0,width=8,resolution=1,highlightthickness=0,activebackground='#282923',troughcolor='#A8A8A8',cursor="hand2",command=lambda *event:self.progress_bar.place(relx=0,relwidth=(float(event[0])/10000-((8/self.s.winfo_width())*float(event[0])/10000))),sliderrelief="flat",sliderlength=8,digits=1)
          self.s.pack(side='top',fill="x")
          self.progress_bar=Label(self.s,bd=0,highlightthickness=0,bg="#FF5C38")
          self.progress_bar.place(relx=-1,y=0,relheight=1)
          self.progress_bar.bind("<Button-1>",lambda event:self.s.set(event.x/self.s.winfo_width()*10000))
          self.videotime=tk.Label(self.frame_2,text="00:00:00/00:00:00",bg="#2E2E36")
          self.videotime.pack(side=tk.LEFT, padx=0)
          self.s.bind("<Button-1>",lambda event:self.s.set(event.x/self.s.winfo_width()*10000))
          self.s.bind("<MouseWheel>",self.click)#滚动调整音量
          self.videotime.bind("<MouseWheel>",self.click)#滚动调整音量
        framemusic=tk.Frame(self.frame_2,bg="#2E2E36")
        framemusic.pack(side=tk.LEFT,padx=8,fill="y")
        framemusic.bind("<MouseWheel>",self.click)#滚动调整音量
        framemusic1=tk.Label(framemusic,text="◀〕",font=("Comic Sans MS",font,"bold"),bg="#2E2E36")
        framemusic1.pack(side=tk.LEFT)
        self.music=tk.Scale(framemusic,from_=0,to=100,bg="#282923",fg='#FF5C38', orient=tk.HORIZONTAL,bd=0,showvalue=0,tickinterval=0,width=8,resolution=1,highlightthickness=0,activebackground='#282923',troughcolor='#A8A8A8',cursor="hand2",command=lambda *event:self.music_Scale.place(relx=0,relwidth=int(event[0])/100,width=-8*(float(event[0])/100)),sliderrelief="flat",sliderlength=8)
        self.music.pack(side="bottom",pady=self.winfo_width()//85)   
        self.music.set(100)
        self.music_Scale=Label(self.music,bd=0,highlightthickness=0,bg="#FF5C38")
        self.music_Scale.place(relx=-1,x=0,y=0,relheight=1,relwidth=1,width=-8)
        self.music.bind("<Button-1>",lambda event:self.music.set(event.x/self.music.winfo_width()*100))
        self.music_Scale.bind("<Button-1>",lambda event:self.music.set(event.x/self.music.winfo_width()*100))
        plicc=[tk.Frame(self.frame_2,bg="#2E2E36")]
        plicc[0].pack(fill=tk.BOTH, expand=tk.YES)
        plicc.append(Label(plicc[0],bg="#FF5C38"))
        plicc.append(Label(plicc[0],bg="#FF5C38"))
        self.bind("<Key>",self.click)#快捷键检测
        self.bind("<KeyRelease>",lambda event:seek_on_arrow(self.player,self.s,event,self.x))
        self.player.set_window(self._canvas.winfo_id())#上方显示视频
        self.frame.bind("<Enter>",lambda *event:self.click(5))#进入时显示
        self.frame.bind("<Leave>",lambda *event:self.click(4))#离开时候变回
        self.edge_bg="#000000"#播放器热区刷成视频底色黑:左/右/下三条热区压在视频上时看不出任何边框(见 view/chrome.py EDGE_BG)
        self.edge=[
          [Label(self,cursor="sb_h_double_arrow",bg="blue"),Label(self,cursor="size_nw_se",bg="blue")],
          [Label(self,cursor="sb_h_double_arrow",bg="blue"),Label(self,cursor="size_ne_sw",bg="blue")],
          [Label(self,cursor="sb_v_double_arrow",bg="blue"),Label(self,cursor="size_ne_sw",bg="blue")],
          [Label(self,cursor="sb_v_double_arrow",bg="blue"),Label(self,cursor="size_nw_se",bg="blue")]
        ]
        self.display(self.edge)#初始摆放并绑定8组边缘缩放(公共逻辑见Window_chrome.display;display里会把热区刷成edge_bg)
        self.apply_alpha()#继承主窗口 ≡ 菜单里选的整窗透明度
        self.frame.bind("<MouseWheel>",self.click)#滚动调整音量
        self.music.bind("<MouseWheel>",self.click)#滚动调整音量
        self.frame_2.bind("<MouseWheel>",self.click)#滚动调整音量
        for i in plicc:
          i.bind("<MouseWheel>",self.click)#滚动调整音量
        framemusic1.bind("<MouseWheel>",self.click)#滚动调整音量
        self.bind('<FocusIn>',lambda event:self.FocusIn_edge(self.edge))#获取焦点,用于做提示,同时用于修复官方所带的一个bug
        self.bind('<FocusOut>',lambda event:self.FocusOut_edge(self.edge))#失去焦点,用于取消状态
        if state.argv[1]!=1:
          self.click(0)


    def zoomednormal(self,*event):
      #标题栏☐:普通窗口最大化/还原。和主窗口一样只铺满工作区(不含任务栏),标题栏/选集栏/进度条/控制条全部保留;
      #真正的"观影全屏"仍由底部控制条的☐(click(self.xsv))进入,两套状态互不干扰。
      try:
        if self.xsv==3:#全屏态下点标题栏☐:先还原成普通窗口,再按下面的普通最大化处理
          self._exit_fullscreen()
        if getattr(self,'_maxed',False):#已最大化 → 还原到最大化前记住的尺寸/位置
          self._maxed=False
          self.Maximize_normal["text"]="☐"
          self._place_window(self.new_x,self.new_y,self.wh1,self.wh2)#参数顺序:x,y,w,h
          self.display(self.edge)#还原成普通窗口,把最大化时收掉的8组缩放边放回来
        else:#普通窗口 → 先记住当前尺寸/位置,再铺满工作区
          self._maxed=True
          self.Maximize_normal["text"]="❐"
          self.wh1=self.winfo_width()
          self.wh2=self.winfo_height()
          self.new_x=self.winfo_x()
          self.new_y=self.winfo_y()
          self.zoomednormalframe=2#旧式"逐帧铺满"循环保持关停,避免它把窗口反复拉满
          if max_win is not None and "win" in sys.platform:
            _geo=max_win.max_win()#工作区(已排除任务栏):x1,y1,x2,y2
            self._place_window(_geo[0],_geo[1],_geo[2]-_geo[0],_geo[3]-_geo[1])
          else:
            self.state('zoomed')#非Windows:交给系统自带的窗口最大化
          self.hide(self.edge)#铺满后收掉8组缩放边:原来没隐藏,窗口贴着屏幕边缘时它们还醒着,鼠标压上去会命中缩放,获得焦点时还会被染成浅蓝#69BCED变成一圈蓝色边框
        self.update_idletasks()
        self.update()#让新geometry真正生效,画布尺寸同步更新
        self.after(80,self._resync_video_window)#尺寸变了重绑VLC渲染窗口,否则视频按旧尺寸显示/留黑边
      except Exception:
        pass

    def click(self, action):
      try:
        if action == 0:
            if self.player.get_state() == 0:
                self.player.resume()
            elif self.player.get_state() == 1:
                pass  # 播放新资源
            else:
                if state.argv[1]!="2":
                    state.current_url=state.argv[2]
                if str(state.argv[1]) in ("2","3") and not str(state.current_url).startswith("http"):
                    # 地址还没解析出来(选集页刚打开/解析失败):别把 cid 或空串喂给播放器,
                    # 解析完成后 _auto_play_ready 会自动开播
                    print("地址解析中,稍后自动开播…")
                    return
                self.player.play(state.current_url)
                self._play_monitor()  # 复用单一监控线程,避免叠加
                self.player.set_marquee()
            self.Pause_start["text"]="  ▏▏"
            self.x=1
        elif action == 1:
            if self.player.get_state() == 1:
                self.player.pause()
            self.x=0
            self.Pause_start["text"]=" ▶ "
        elif action == 2 or action == 7:#标题栏☐/底栏☐:进入"观影全屏"(用统一的enter/exit,避免两套全屏状态叠加后退不出去)
            self._enter_fullscreen()
        elif action == 3 or action == 8:#退出全屏,还原普通窗口
            self._exit_fullscreen()
        elif action == 4:
            if self.xsv==3:
              if state.argv[1]!="4":
                self.frame_2.pack_forget()
        elif action == 5:
            if self.xsv==3:
              self.frame_2.pack(side='bottom',fill="x")
        elif action == 6:
              self.Multipless=(self.Multipless+1)-(self.Multipless+1)//5*5
              if self.Multipless==1:
                self.Multiple["text"]="倍数:正常"
              else:
                self.Multiple["text"]=f"倍数:{self.Multiples[self.Multipless]}x"
              self.player.set_rate(self.Multiples[self.Multipless])
        elif action == 9:
              state.nonono=True
        elif action.keycode == 27:#Esc:无论从哪种入口进入的全屏态都能还原
            if self.xsv==3 or getattr(self,'xxssxs',7)==8:
                self._exit_fullscreen()
        elif action.keycode ==37:
            self.s.set(self.s.get()-100)
            if self.player.get_state() == 1:
                self.player.pause()
        elif action.keycode ==39 :
            self.s.set(self.s.get()+100)
            if self.player.get_state() == 1:
                self.player.pause()
        elif action.keycode ==32:
            self.click(self.x)
        elif action.keycode == 38:
          if self.set_ratio!=2:
            self.set_ratio=self.set_ratio+1
            self.player.set_ratio(self.set_ratios[self.set_ratio])
        elif action.keycode == 40:
          if self.set_ratio!=0:
            self.set_ratio=self.set_ratio-1
            self.player.set_ratio(self.set_ratios[self.set_ratio])
      except:
          pass
      try:
        if action.delta == 120:
              self.music.set(self.music.get()+10)
        elif action.delta == -120:
              self.music.set(self.music.get()-10)
      except:
          pass


    def _enter_fullscreen(self):
        #进入"观影全屏":记住当前普通窗口的尺寸/位置→把窗口铺满可用屏幕→隐藏标题条/选集栏/底栏按钮行。
        #底部frame+进度条仍保留当"触手",鼠标移入会自动浮出完整控制条(见click(4)/(5)),实现全屏下的自动弹出逻辑
        try:
            if self.xsv==3:#已在全屏,再次触发视为切换回普通窗口
                self._exit_fullscreen()
                return
            self.zoomednormalframe=2#先关停旧式"逐帧铺满"循环再记忆尺寸;否则循环会在记忆之后又把窗口拉满,退出全屏时还原的就是全屏尺寸
            try:
                self.state('normal')#若窗口当前处于系统最大化(zoomed),先归位再记忆,否则记住的是最大化尺寸而非用户窗口尺寸
                self.update_idletasks()
            except Exception:
                pass
            if getattr(self,'_maxed',False):#标题栏普通最大化状态下进全屏:先还原成最大化前的尺寸,退出全屏才回得到用户原来的窗口大小
                self._maxed=False
                self.Maximize_normal["text"]="☐"
                self._place_window(self.new_x,self.new_y,self.wh1,self.wh2)#参数顺序:x,y,w,h
            self.wh1=self.winfo_width()
            self.wh2=self.winfo_height()
            self.new_x=self.winfo_x()
            self.new_y=self.winfo_y()
            self.xxssxs=7
            self.xsv=3
            self.xxsxs.pack_forget()
            self.frame_3.pack_forget()
            try:
                self.frame_2.pack_forget()
            except Exception:
                pass
            try:
                #真全屏:铺满整块屏幕(含任务栏),并定位到播放窗口当前所在的显示器。max_win()给的是排除了任务栏的工作区,不能用于真全屏
                geo=self._full_screen_geo()
                self._was_topmost=bool(self.attributes('-topmost'))#记下全屏前的置顶状态,退出时还原
                self.attributes('-topmost',True)#全屏窗口置于任务栏之上,否则任务栏会压在窗口上,底部"触手"无法被鼠标悬停触发
                self._place_window(geo[0],geo[1],geo[2],geo[3])#真正落位:先Tk,再校验,不一致用SetWindowPos强制
            except Exception:
                self.state("zoomed")#非Windows等无法精确定位显示器时的兜底(系统最大化)
            self.hide(self.edge)
            self.Maximize["text"]="❐"
            self.update_idletasks()
            self.update()#update_idletasks只重排布局,这里再走一次完整事件循环,让新geometry真正生效、画布尺寸同步更新
            self.after(80,self._resync_video_window)#延迟到窗口resize完成后重绑渲染窗口,否则视频可能仍按旧尺寸显示
            self.after(260,self._resync_video_window)#再补一次:跨越任务栏/DPI缩放时窗口尺寸就位更晚,补绑确保视频真正铺满
        except Exception:
            pass

    def _full_screen_geo(self):
        #返回播放窗口当前所在显示器的完整矩形(x,y,宽,高)。rcMonitor含任务栏所在区域;max_win()算的是排除了任务栏的工作区,所以这里直接查显示器
        try:
            import ctypes
            from ctypes import wintypes
            class _MI(ctypes.Structure):
                _fields_=[("cbSize",wintypes.DWORD),("rcMonitor",wintypes.RECT),
                          ("rcWork",wintypes.RECT),("dwFlags",wintypes.DWORD)]
            _u32=ctypes.windll.user32
            #用窗口自己的句柄问"我在哪块屏",比之前的"自己算窗口中心点"稳:窗口跨屏、坐标被overrideredirect包一层都不受影响。
            #winfo_id()对Toplevel可能拿到子窗口,GetAncestor(GA_ROOT=2)才是真正被摆放的顶层窗口。
            #这里用本地WINFUNCTYPE包装而不是改_u32.MonitorFromWindow的argtypes/restype:windll的属性是带缓存的同一对象,改了会污染别处(64位HMONITOR默认按int返回会被截断)
            _GetAncestor=ctypes.WINFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint)(("GetAncestor",_u32))
            _MonitorFromWindow=ctypes.WINFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD)(("MonitorFromWindow",_u32))
            _GetMonitorInfoW=ctypes.WINFUNCTYPE(wintypes.BOOL,ctypes.c_void_p,ctypes.POINTER(_MI))(("GetMonitorInfoW",_u32))
            _mi=_MI(); _mi.cbSize=ctypes.sizeof(_MI)
            _hm=_MonitorFromWindow(_GetAncestor(ctypes.c_void_p(self.winfo_id()),2),2)#2=MONITOR_DEFAULTTONEAREST:最近的那块(窗口跨屏时取交集更大的那块)
            if _hm and _GetMonitorInfoW(_hm,ctypes.byref(_mi)):
                _l=_mi.rcMonitor.left; _t=_mi.rcMonitor.top
                if _mi.rcMonitor.right>_l and _mi.rcMonitor.bottom>_t:#矩形异常(0宽/0高)时兜底,否则会拿0x0的geometry把窗口缩没
                    return (_l,_t,_mi.rcMonitor.right-_l,_mi.rcMonitor.bottom-_t)
        except Exception:
            pass
        return (0,0,self.winfo_screenwidth(),self.winfo_screenheight())#兜底:整块主屏(含任务栏)

    def _place_window(self,x,y,w,h):
        #把窗口精确摆到(x,y,w,h),物理像素,多屏含负坐标(x=-1920/y=-826这类)。
        #为什么要绕这一圈:Tk的geometry在"窗口正处于系统最大化(zoomed)"时会被Windows整条丢弃——连xy带尺寸一起不生效,表现就是"全屏位置怎么设都没用"。
        #所以三步走:先退出最大化(并走完整事件循环让Windows把还原消息处理掉)→交给Tk→再比对实际位置,对不上就用SetWindowPos直接摆。
        try:
            if self.state()=="zoomed":
                self.state('normal')
                self.update()#只走update_idletasks不够:不处理Windows消息,窗口在系统眼里仍是最大化,紧接着的geometry照样被丢
        except Exception:
            pass
        try:
            #负坐标必须写成"+-1920"这种形式:+号后带负号才是绝对坐标;若只写-1920,Tk会当成"距屏幕右边缘1920"(全屏就会跑到主屏去)
            self.geometry(f"{w}x{h}+{x}+{y}")
            self.update()
        except Exception:
            pass
        try:
            if (self.winfo_rootx(),self.winfo_rooty(),self.winfo_width(),self.winfo_height())==(int(x),int(y),int(w),int(h)):
                return#已经就位,不必再动
        except Exception:
            return
        try:#兜底:Tk没落位(窗口仍被判为最大化/被系统改回)时用Win32直接摆,保证xy一定生效
            import ctypes
            from ctypes import wintypes
            _u32=ctypes.windll.user32
            _GetAncestor=ctypes.WINFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint)(("GetAncestor",_u32))
            _SetWindowPos=ctypes.WINFUNCTYPE(wintypes.BOOL,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_uint)(("SetWindowPos",_u32))
            _hwnd=_GetAncestor(ctypes.c_void_p(self.winfo_id()),2)
            if _hwnd:
                _SetWindowPos(_hwnd,ctypes.c_void_p(-1),int(x),int(y),int(w),int(h),0x0004|0x0010)#SWP_NOZORDER|SWP_NOACTIVATE,置顶态已由attributes('-topmost')管
                self.update()
        except Exception:
            pass


    def _resync_video_window(self):#窗口尺寸变化后重新把VLC绑到画布句柄:VLC不一定会自己跟上父窗口的新尺寸,重绑一次强制它按新画布重建渲染窗口(解决全屏后视频不铺满/留黑边)
        try:
            if self._canvas.winfo_exists():
                self.player.set_window(self._canvas.winfo_id())
        except Exception:
            pass


    def _exit_fullscreen(self):
        #退出全屏,还原普通窗口:关停铺满循环→按进入前记忆的尺寸/位置恢复标题条/选集栏/进度条/控制条/画布布局
        try:
            self.xsv=2
            self.xxssxs=7
            self.zoomednormalframe=2#关停循环,确保窗口不再被拉回全屏
            for _w in (self._canvas,self.frame,self.frame_3,self.xxsxs,self.frame_2):
                try:
                    _w.pack_forget()
                except Exception:
                    pass
            self.xxsxs.pack(side='top',fill="x")
            if state.argv[1]=="2":
                self.frame_3.pack(side=tk.RIGHT,fill="y")
            self.frame_2.pack(side='bottom',fill="x")
            self.frame.pack(side='bottom',fill="x")
            self._canvas.pack(fill="both",expand=tk.YES)
            self._place_window(getattr(self,'new_x',self.winfo_x()),getattr(self,'new_y',self.winfo_y()),getattr(self,'wh1',self.winfo_width()),getattr(self,'wh2',self.winfo_height()))#记忆值缺失时退回当前尺寸/位置,避免还原成0x0;同样走落位校验,多屏负坐标也能还原回原屏
            try:
                self.state('normal')#若兜底路径用过系统最大化,这里取消
            except Exception:
                pass
            try:
                self.attributes('-topmost',getattr(self,'_was_topmost',False))#取消全屏置顶,还原进入前的置顶状态
            except Exception:
                pass
            self.display(self.edge)
            self.Maximize["text"]="☐"
            self.update_idletasks()
            self.update()#让还原后的geometry真正生效
            self.after(80,self._resync_video_window)#还原尺寸后同样重绑渲染窗口,否则视频会停在全屏尺寸
        except Exception:
            pass
