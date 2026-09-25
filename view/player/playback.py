# -*- coding: utf-8 -*-
"""播放核心:建窗、后台解析播放地址、就绪后自动开播、换集监控、幂等释放。(从 main.py 的 App 拆出)

原 App.__init__ / _load_play_info / _current_ep_id / _apply_play_info /
_auto_play_ready / _close_player / _play_monitor / _speed_wrap / _tab_click

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



class PlaybackMixin(object):


    def __init__(self,i):
        super().__init__()
        self.window=self#公共窗口逻辑统一通过 self.window 访问真正的顶层窗口
        self._set_the_after=1#与原版App Set_the延时一致(1ms;VG默认100ms)
        if i==1:
          self.no=self
        else:
          self.no=i
        self.xxssxs=7
        self.xsv=2
        self._maxed=False   # 标题栏☐的普通最大化状态(False=普通窗口,True=已铺满工作区)
        self.x=0
        state.nonono=False
        self.Multipless=1
        self.loadsi=0
        self.Multiples=[0.5,1,1.25,1.5,2]
        self.set_ratios=["16:9","4:3",""]
        self.set_ratio=2
        self.html=""        # 剧集信息原始文本(QZOutputJson=…),由后台线程填充;失败也是空串,不影响窗口打开
        self.Anthologyggg=0 # 右侧标签当前页:1选集/2评论(默认选集)
        self._auto_played=False      # 是否已自动开播(只开一次)
        self._speed_on=False         # 换集/进度监控线程是否运行中
        self._autoplay_blocked=False
        self.url=""                 # 换集监控用:上一次已送进播放器的地址(空串表示还没解析好)
        self.p=False                 # 选集是否为"分页宫格"布局(由数据判定,默认False防止未定义)
        self._last_hl=None           # 上次高亮的选集索引(用于换集后刷新高亮)
        self._panel_w=0              # 右侧选集/评论面板宽度(拖分隔条调整,0=还没量过)
        self._panel_ratio=None       # 拖出来的面板宽占窗口宽的比例,窗口缩放时按它还原
        self._panel_last_ww=None     # 上次记下的窗口宽,避免 <Configure> 里反复重算
        self._pdrag_x=None           # 拖分隔条时的按下位置(None=当前没在拖)
        self._pdrag_w=0              # 按下那一刻的面板宽
        self._reuse_danmu=False      # 拖动改宽后的重建标记:评论页复用已有弹幕缓存,不重新联网拉取
        self._fail_label=None        # "取不到播放地址"的提示标签(内容加密/会员/网络);能播时清掉
        self._fail_msged=""          # 面板隐藏时已弹过的失败说明:同一条不重复弹
        self._play_fail_msg=""       # 本窗口后台解析失败的原因:随解析一起记下,回主线程用(避免被别的窗口覆盖)
        self.player = tkPlayer()
        self._player_closed=False     #播放器是否已释放:关闭按钮和监控线程都会触发释放,用标志保证只释放一次
        self.title("VG视频")
        self.geometry(f'{(self.winfo_screenwidth()-self.winfo_screenwidth()//4)}x{(self.winfo_screenheight()-self.winfo_screenheight()//6)}+{(self.winfo_screenwidth()-(self.winfo_screenwidth()-self.winfo_screenwidth()//4))//2}+{(self.winfo_screenheight()-(self.winfo_screenheight()-self.winfo_screenheight()//6))//2}')
        self.frameless()#去掉标准控件边框(各系统无边框策略不同,见Window_chrome.frameless)
        self.after(1, lambda: self.taskbar(self))#恢复任务栏显示
        _safe_attributes(self,("-transparentcolor","blue"))#透明色仅Windows支持
        self.update()
        self.create_video_view()
        state.active_player=self  # 供 uri 选集切换后触发自动开播
        if state.argv[1]=="2":
            # 选集等播放信息放后台线程获取:能获取就正常展示/自动开播,获取失败窗口也能正常打开并给出提示
            try:
                _th=Thread(target=self._load_play_info)
                _th.daemon = True
                _th.start()
            except Exception:
                pass


    def _load_play_info(self):#后台线程:拉取剧集信息+解析当前集播放地址,完成后回主线程刷新界面
        try:
            _raw=_qq_episodes(state.argv[2])#选集:旧 s.video.qq.com/get_playsource 已下线,改用 GetPageData
        except Exception:
            _raw=""
        _ok=bool(_raw)
        if _ok:
            self.html=_raw
            # 顺带在后台解析当前集播放地址(用户自修解析接口后即自动开播;失败不影响窗口)
            try:
                _id=self._current_ep_id()
                if _id:
                    _res=_resolve_url(_id)
                    if _res:
                        state.current_url=_res+"&"+str(_id)+"=vg"
                        self.loadsi=1
                    else:
                        self._play_fail_msg=play_fail_msg()#解析失败(加密/会员/网络):连原因一起带回主线程提示
            except Exception:
                pass
        try:
            self.after(0,lambda:self._apply_play_info(_ok))
        except Exception:
            pass

    def _current_ep_id(self):#从已获取的剧集信息里取当前集(vgi)的id,失败返回None
        try:
            _j=loads(self.html[13:-1] if self.html.startswith("QZOutputJson") else self.html)
            _pi=_j.get("PlaylistItem") or {}
            _pl=_pi.get("videoPlayList") or []
            if _pl and isinstance(_pl,list):
                _v=max(0,min(len(_pl)-1,state.current_episode))
                return _pl[_v].get("id") or (_pl[_v].get("playUrl") or "")
            return None
        except Exception:
            return None

    def _apply_play_info(self,_ok):#主线程:根据结果刷新播放器右侧(片名+选集/提示),保证任何情况窗口都可用
        try:
            if _ok:
                try:
                    _t=_qq_ep_title(self.html,state.current_episode)#当前集显示名(play_title,如"斗罗大陆Ⅱ绝世唐门 第001话")
                    if not _t:#兜底:退到剧名(PlaylistItem.title)
                        _t=str(((_json_load(self.html).get("PlaylistItem") or {}).get("title")) or "")
                    self.name["text"]=_t or state.argv[2]
                except Exception:
                    try: self.name["text"]=state.argv[2]
                    except Exception: pass
                try:
                    self.Anthology(self.frame_3,1)#信息正常:构建选集列表/当前集高亮
                except Exception as _ant_err:
                    print("选集列表构建失败:",_ant_err)
                # 解析地址可用时自动开播;解析失败窗口保持可用,等用户点选集/稍后重试
                try: self._auto_play_ready()
                except Exception: pass
                if not str(state.current_url or "").startswith("http"):#选集信息拿到了却取不到地址:说明原因,别只留个空窗口
                    self._play_fail_hint(getattr(self,"_play_fail_msg",""))
            else:
                try:
                    self.name["text"]=state.argv[2]
                except Exception:
                    pass
                try:
                    if not getattr(self,"_fail_tipped",False):
                        self._fail_tipped=True
                        tk.Label(self.frame_3,text="选集信息获取失败\n请检查网络,或稍后点击[选集]重试",bg="#26262B",fg="#DBDBDC",wraplength=int(self.winfo_width()//3.5)).pack(pady=10)
                except Exception:
                    pass
        except Exception:
            pass

    def _play_fail_hint(self,msg=""):#主线程:把"取不到播放地址"的原因告诉用户,别让 TA 对着空白播放器
        # msg 来自解析服务(如"该内容是加密视频(Widevine/PlayReady DRM)…");没有就退一句通用文案。
        # 右侧面板可见时挂个标签(反复换集就地更新,不堆提示);面板被隐藏时改弹窗,保证提示一定看得见。
        try:
            _txt=str(msg or "").strip() or "没有取到可播放的地址(会员 / 权益 / 登录态 / 网络),可稍后重试"
            _f=getattr(self,"frame_3",None)
            # winfo_manager() 能同步反映 pack_forget() 的结果(用 ismapped 会因 Tk 延迟更新而误判)
            if _f is None or _f.winfo_manager()!="pack":#右侧面板被隐藏(如未收录/需VIP):标签没处显示,用弹窗
                if str(getattr(self,"_fail_msged",""))!=_txt:
                    self._fail_msged=_txt
                    try: tkinter.messagebox.showinfo("无法播放",_txt)
                    except Exception: print("无法播放:",_txt)
                return
            _lb=getattr(self,"_fail_label",None)
            if _lb is not None and _lb.winfo_exists():
                _lb.configure(text=_txt)
                return
            _lb=tk.Label(_f,text=_txt,bg="#26262B",fg="#DBDBDC",justify="center",
                         wraplength=max(160,int(self.winfo_width()//3.5)))
            _lb.pack(pady=10)
            self._fail_label=_lb
        except Exception:
            pass

    def _play_fail_clear(self):#主线程:能播了就把失败提示收掉
        _lb=getattr(self,"_fail_label",None)
        self._fail_label=None
        self._fail_msged=""
        if _lb is not None:
            try: _lb.destroy()
            except Exception: pass

    def _auto_play_ready(self):#主线程:解析地址就绪后自动开播(仅一次,失败就等用户重试),并保持换集监控线程
        try:
            _u=str(state.current_url or "")
            if _u.startswith("http"):
                self._play_fail_clear()#地址已就绪:收掉之前的失败提示
            if getattr(self,"_auto_played",False):
                return
            if not _u.startswith("http"):
                return
            if getattr(self,"_autoplay_blocked",False):
                return
            self._autoplay_blocked=True
            _st=getattr(self.player,"get_state",lambda:None)()
            if _st in (1,3):#已在播放/暂停中则交给监控线程处理
                self._auto_played=True
                return
            self._auto_played=True
            try:
                self.Pause_start["text"]="  ▏▏"
                self.x=1
            except Exception:
                pass
            try:
                self.player.play(state.current_url)
                self.player.set_marquee()
            except Exception:
                pass
            try:
                self._play_monitor()
            except Exception:
                pass
        except Exception:
            pass

    def _close_player(self):#释放播放器:幂等且容忍属性已被删除(点×时主线程和监控线程会同时在跑,重复释放就会报 AttributeError:'App' object has no attribute 'player')
        if getattr(self,"_player_closed",False):
            return
        self._player_closed=True
        _p=getattr(self,"player",None)
        if _p is None:
            return
        try: _p.release()
        except Exception: pass
        try: _p.stop()
        except Exception: pass
        self.player=None#保留属性名(置None),避免其它回调再访问时报 AttributeError


    def _play_monitor(self):#启动换集/进度监控线程(同一播放器只保持一条,可一直响应后续换集)
        try:
            if getattr(self,"_speed_on",False):
                return
            self._speed_on=True
            _th=Thread(target=self._speed_wrap)
            _th.daemon = True
            _th.start()
        except Exception:
            try: self._speed_on=False
            except Exception: pass

    def _speed_wrap(self):#Speed_of_progress 的守护包装:线程结束/异常后释放监控标记
        try:
            self.Speed_of_progress()
        except Exception:
            pass
        finally:
            try: self._speed_on=False
            except Exception: pass

    def _tab_click(self,_tab):#右侧"选集/评论"点击:信息没到位则去后台重试,避免在主线程里卡网络
        if _tab==1 and (not self.html) and state.argv[1]=="2":
            try:
                Thread(target=self._load_play_info).start()
            except Exception:
                pass
            return
        try:
            self.Anthology(self.frame_3,_tab)
        except Exception as _ant_err:
            print("Anthology 切换失败:",_ant_err)
