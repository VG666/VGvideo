# -*- coding: utf-8 -*-
"""无边框窗口公共逻辑 —— 一个大类单独成模块

Window_chrome:8向边缘缩放、边框显示/隐藏与焦点、无边框窗口拖动、任务栏恢复。
约定真正的顶层窗口保存在 self.window(VG_video.window 是内置Tk;App 自身即窗口,初始化时 self.window=self)。

另附输入框剪贴板助手(复制/剪切/粘贴)。
"""
from tkinter import *
import tkinter as tk

from view.image import _safe_attributes
from view.icons import App_icon
from model.paths import (IS_WINDOWS, IS_LINUX, windll,
                     GWL_EXSTYLE, WS_EX_APPWINDOW, WS_EX_TOOLWINDOW)

EDGE_BG="#303038"#8组边缘缩放热区Label的填充色:必须等于窗口底色,视觉上等于"没有边框"。
#以前用的是 bg="blue"+窗口-transparentcolor blue:靠色键把热区做成透明,但色键区域在Windows下连鼠标一起穿透,
#所以只能靠FocusIn把它染成#69BCED才点得动 —— 代价就是窗口四周永远挂着一圈浅蓝边框。改成实心底色后热区始终可点,边框彻底看不见。

class Window_chrome(object):#窗口公共逻辑:8向边缘缩放、边框显示/隐藏与焦点、无边框窗口拖动、任务栏恢复。约定真正的顶层窗口保存在 self.window(VG_video.window 是内置Tk;App 自身即窗口,初始化时 self.window=self)。
    def _ghost(self,parent,w,h,x,y):#创建"拖拽预览"用的蓝色透明虚框
        g=Toplevel(parent)#次窗口依赖于主窗口
        g.geometry(f"{w}x{h}+{x}+{y}")#将位置调成这个宽高
        g.overrideredirect(True)#去掉边框
        g.withdraw()#点击的时候隐藏,真正移动的时候才显示
        _safe_attributes(g,("-transparentcolor","blue"))#透明色仅Windows支持;失败时保留半透明蓝色预览框
        g.attributes("-alpha",0.5)#透明度,让边框有一定的透明程度
        g.attributes('-topmost',1)
        canvas=Canvas(g,highlightthickness=3,highlightbackground='#D7D6DC',bg="blue")#全屏显示,留一点边框,其实所显示的边框就是靠留下的边框
        canvas.pack(fill="both",expand=tk.YES)#全屏显示
        return g
    def Edge_size_rectification(self,event,edge):#缩放拖拽中:实时把虚框调成新大小/位置(edge1-8:左/右/上/下/左上/右上/左下/右下)
        win=self.window
        if edge==1:
            self.Dotted_frame_edge.deiconify()
            self.Dotted_frame_edge.geometry(f"{win.winfo_width()-event.x}x{win.winfo_height()}+{event.x+win.winfo_x()}+{win.winfo_y()}")
        elif edge==2:
            self.Dotted_frame_edge.deiconify()
            self.Dotted_frame_edge.geometry(f"{win.winfo_width()+event.x}x{win.winfo_height()}+{win.winfo_x()}+{win.winfo_y()}")
        elif edge==3:
            self.Dotted_frame_edge.deiconify()
            self.Dotted_frame_edge.geometry(f"{win.winfo_width()}x{win.winfo_height()-event.y}+{win.winfo_x()}+{event.y+win.winfo_y()}")
        elif edge==4:
            self.Dotted_frame_edge.deiconify()
            self.Dotted_frame_edge.geometry(f"{win.winfo_width()}x{win.winfo_height()+event.y}+{win.winfo_x()}+{win.winfo_y()}")
        elif edge==5:
            self.Dotted_frame_edge.deiconify()
            self.Dotted_frame_edge.geometry(f"{win.winfo_width()-event.x}x{win.winfo_height()-event.y}+{event.x+win.winfo_x()}+{event.y+win.winfo_y()}")
        elif edge==6:
            self.Dotted_frame_edge.deiconify()
            self.Dotted_frame_edge.geometry(f"{win.winfo_width()+event.x}x{win.winfo_height()-event.y}+{win.winfo_x()}+{event.y+win.winfo_y()}")
        elif edge==7:
            self.Dotted_frame_edge.deiconify()
            self.Dotted_frame_edge.geometry(f"{win.winfo_width()-event.x}x{win.winfo_height()+event.y}+{event.x+win.winfo_x()}+{win.winfo_y()}")
        elif edge==8:
            self.Dotted_frame_edge.deiconify()
            self.Dotted_frame_edge.geometry(f"{win.winfo_width()+event.x}x{win.winfo_height()+event.y}+{win.winfo_x()}+{win.winfo_y()}")
    def Edge_sizing_release_mouse(self,event):#缩放结束:把虚框的大小/位置正式应用给窗口
        try:
            f=self.Dotted_frame_edge
            self.wh1,self.wh2=f.winfo_width(),f.winfo_height()
            self.window.geometry(f"{self.wh1}x{self.wh2}+{f.winfo_x()}+{f.winfo_y()}")#将位置调成这个宽高
            self.new_x,self.new_y=f.winfo_x(),f.winfo_y()#边缘缩放也会挪位置,一并记下,供"最大化→还原"回到用户实际摆放的地方
            f.destroy()#将这个窗口删除
        except:
            pass
    def Edge_size_rectification_button(self,event,edge):#按下任一边缘/角:创建缩放预览虚框
        win=self.window
        self.Dotted_frame_edge=self._ghost(win,win.winfo_width(),win.winfo_height(),win.winfo_x(),win.winfo_y())
    def _edge_bg(self):#带回退,子类可用 self.edge_bg 覆盖底色
        return getattr(self,'edge_bg',EDGE_BG)
    def _paint_edges(self):#把8组热区刷成底色:不再随焦点变色(#69BCED那圈浅蓝边框就是它画出来的),热区本身依然不透明、可接收鼠标
        color=self._edge_bg()
        for pair in getattr(self,'edge',[]):
            for label in pair:
                try:
                    label.configure(bg=color,bd=0,highlightthickness=0)
                except Exception:
                    pass
    def FocusIn_edge(self,event):#获取焦点:原来在这里把边缘染成浅蓝做"边框提示",现在保持隐形,只做一次刷新(热区需要的时候重新配置一下)
        self._paint_edges()
    def FocusOut_edge(self,event):#失去焦点:同样保持隐形
        self._paint_edges()
    def hide(self,event):#隐藏边界
        for i in event:
            i[0].place_forget()
            i[1].place_forget()
    def display(self,event):#显示边界,并把8组边缘/角绑定到缩放逻辑
        self._paint_edges()#先刷成隐形色再摆放,避免出现瞬间的蓝边
        e=self.edge
        e[0][0].place(width=2,relheight=1)
        e[0][0].bind("<Button-1>",lambda event:self.Edge_size_rectification_button(event,1))
        e[0][0].bind("<B1-Motion>",lambda event:self.Edge_size_rectification(event,1))
        e[0][0].bind("<ButtonRelease-1>",self.Edge_sizing_release_mouse)
        e[1][0].place(relx=1,x=-2,width=2,relheight=1)
        e[1][0].bind("<Button-1>",lambda event:self.Edge_size_rectification_button(event,2))
        e[1][0].bind("<B1-Motion>",lambda event:self.Edge_size_rectification(event,2))
        e[1][0].bind("<ButtonRelease-1>",self.Edge_sizing_release_mouse)
        e[2][0].place(relwidth=1,height=2)
        e[2][0].bind("<Button-1>",lambda event:self.Edge_size_rectification_button(event,3))
        e[2][0].bind("<B1-Motion>",lambda event:self.Edge_size_rectification(event,3))
        e[2][0].bind("<ButtonRelease-1>",self.Edge_sizing_release_mouse)
        e[3][0].place(rely=1,y=-2,relwidth=1,height=2)
        e[3][0].bind("<Button-1>",lambda event:self.Edge_size_rectification_button(event,4))
        e[3][0].bind("<B1-Motion>",lambda event:self.Edge_size_rectification(event,4))
        e[3][0].bind("<ButtonRelease-1>",self.Edge_sizing_release_mouse)
        e[0][1].place(width=3,height=3)
        e[0][1].bind("<Button-1>",lambda event:self.Edge_size_rectification_button(event,5))
        e[0][1].bind("<B1-Motion>",lambda event:self.Edge_size_rectification(event,5))
        e[0][1].bind("<ButtonRelease-1>",self.Edge_sizing_release_mouse)
        e[1][1].place(relx=1,x=-3,y=0,width=3,height=3)
        e[1][1].bind("<Button-1>",lambda event:self.Edge_size_rectification_button(event,6))
        e[1][1].bind("<B1-Motion>",lambda event:self.Edge_size_rectification(event,6))
        e[1][1].bind("<ButtonRelease-1>",self.Edge_sizing_release_mouse)
        e[2][1].place(rely=1,y=-3,width=3,height=3)
        e[2][1].bind("<Button-1>",lambda event:self.Edge_size_rectification_button(event,7))
        e[2][1].bind("<B1-Motion>",lambda event:self.Edge_size_rectification(event,7))
        e[2][1].bind("<ButtonRelease-1>",self.Edge_sizing_release_mouse)
        e[3][1].place(relx=1,rely=1,x=-3,y=-3,width=3,height=3)
        e[3][1].bind("<Button-1>",lambda event:self.Edge_size_rectification_button(event,8))
        e[3][1].bind("<B1-Motion>",lambda event:self.Edge_size_rectification(event,8))
        e[3][1].bind("<ButtonRelease-1>",self.Edge_sizing_release_mouse)
    def _drag_locked(self):#当前窗口是否禁止拖动标题栏(最大化/全屏):窗口已经铺满,再拖只会拖出"铺满尺寸的普通窗口",位置与按钮状态全对不上
        if getattr(self,'_maxed',False):#播放器的标题栏☐普通最大化(False=普通窗口)
            return True
        if not getattr(self,'Maximize_ty',True):#主窗口:Maximize_ty=False 表示正处于最大化
            return True
        if getattr(self,'xsv',2)==3 or getattr(self,'xxssxs',7)==8:#播放器的"观影全屏"
            return True
        return False
    def _drop_ghost(self):#安全销毁拖动预览虚框:拖动被挡掉/中途异常时也不能把蓝框留在桌面上
        f=getattr(self,'Dotted_frame',None)
        self.Dotted_frame=None
        if f is not None:
            try:
                f.destroy()
            except Exception:
                pass
    def mobile_2(self,event):#按下标题栏:创建移动预览虚框,记录鼠标在窗口内偏移
        win=self.window
        self.mobile=0#先清掉上一次的标记,避免残留的"移动中"状态
        self._drop_ghost()#上一次留下的虚框先收掉,不然会越拖越多
        if self._drag_locked():
            return#最大化/全屏下不响应拖动:原来照拖,蓝色虚框跟着鼠标跑,松手后铺满的窗口被拖走且最大化按钮还原不回去
        try:
            w=getattr(self,'wh1',0) or win.winfo_width()#wh1/wh2 是"普通窗口尺寸":最大化时它记的是还原尺寸,这里作为拖动预览的宽高
            h=getattr(self,'wh2',0) or win.winfo_height()
            self.Dotted_frame=self._ghost(win,w,h,win.winfo_x(),win.winfo_y())
            self.x,self.y=event.x,event.y#记录鼠标在窗口的位置
        except Exception:
            self.Dotted_frame=None
            return
        self.mobile=1#虚框真的建起来了才算"移动中",否则一旦建框失败,mobile 卡在 1 会让后续松开事件误改窗口位置
    def mobile_1(self,event):#移动中:虚框跟着鼠标走(未真正移动不显示,避免误点闪现)
        if getattr(self,'mobile',0)!=1:#没按下标题栏(或已被最大化挡掉)时不处理,免得虚框乱跑
            return
        try:
            x=event.x_root-self.x#算出宽的位置
            y=event.y_root-self.y#算出高的位置
            self.Dotted_frame.deiconify()#显示出来
            self.Dotted_frame.geometry(f"+{x}+{y}")#移动虚框
        except:
            pass
    def mobile_3(self,event):#松开鼠标:把虚框位置应用到窗口(保持当前大小,子类通过 _drag_finished 处理全屏状态)
        if getattr(self,'mobile',0)!=1:#没真正拖动过(最大化挡掉/虚框没建起来)就直接返回,别把状态改花
            self._drop_ghost()
            return
        self.mobile=0#先复位:下面任何一步出问题都不会把"移动中"残留到下一次
        f=getattr(self,'Dotted_frame',None)
        self.Dotted_frame=None
        if f is None:
            return
        try:
            x,y=f.winfo_x(),f.winfo_y()#虚框停在哪,窗口就搬去哪
        except Exception:
            x,y=getattr(self,'new_x',0),getattr(self,'new_y',0)
        try:
            f.destroy()#将这个窗口删除
        except Exception:
            pass
        #位置记忆必须在"窗口还没搬"之前写:geometry 后 Tk 不会立刻生效,此时 winfo_x() 读到的还是旧坐标,
        #拿它记位置会得到"拖动等于没动",下一次最大化再还原就跳回旧位置
        self.new_x,self.new_y=x,y
        try:
            self.window.geometry(f"+{x}+{y}")#把窗口搬到虚框的位置
            self.window.update_idletasks()#让位置立刻生效,后面钩子/其它逻辑读 winfo 才是新值
        except Exception:
            pass
        self._drag_finished()#子类钩子
    def _drag_finished(self):#拖拽结束钩子,子类按需覆盖
        pass
    def apply_alpha(self,alpha=None):#整窗透明度:1.0=完全不透明。win/mac 支持 -alpha;linux 多数WM不支持,失败就保持不透明,不影响其它逻辑
        try:
            import model.state as state
        except Exception:
            return None
        if alpha is not None:
            state.window_alpha=alpha
        value=getattr(state,'window_alpha',1.0)
        try:
            getattr(self,'window',self).attributes('-alpha',float(value))
        except Exception:
            pass
        return value
    def _win_show_in_taskbar(self,window):#Windows:overrideredirect窗口默认被Tk当成工具窗藏出任务栏,这里清掉TOOLWINDOW并强制APPWINDOW
        try:
            hwnd=window.winfo_id()
            if not hwnd:
                return
            parent=windll.user32.GetParent(hwnd)
            if parent:
                hwnd=parent
            ex=windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex=(ex & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
            windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
        except Exception:
            pass
    def _x11_undecorated(self,window):#Linux(X11):去掉WM装饰但保留"普通窗口"类型,无边框的同时任务栏/面板仍有按钮;失败返回False
        try:
            from ctypes import CDLL, c_void_p, c_char_p, c_int, c_ulong
            x11=CDLL("libX11.so.6")
            x11.XOpenDisplay.restype=c_void_p
            x11.XOpenDisplay.argtypes=[c_char_p]
            display=x11.XOpenDisplay(None)
            if not display:
                return False
            x11.XInternAtom.restype=c_ulong
            x11.XInternAtom.argtypes=[c_void_p,c_char_p,c_int]
            motif=x11.XInternAtom(display,b"_MOTIF_WM_HINTS",0)
            if not motif:
                return False
            wid=window.winfo_id()
            if not wid:
                return False
            hints=(c_ulong*5)(2,0,0,0,0)#flags=2(MWM_HINTS_DECORATIONS),decorations=0:去掉标题栏/边框
            x11.XChangeProperty.argtypes=[c_void_p,c_ulong,c_ulong,c_ulong,c_int,c_int,c_void_p,c_int]
            x11.XChangeProperty(display,wid,motif,motif,32,0,hints,5)
            x11.XFlush.argtypes=[c_void_p]
            x11.XFlush(display)
            return True
        except Exception:
            return False
    def frameless(self):#应用"无边框":win/mac用overrideredirect(任务栏由taskbar恢复);linux改用X11去装饰的普通窗口(天然有面板按钮)
        w=self.window
        if IS_LINUX and self._x11_undecorated(w):
            try:
                w.overrideredirect(False)
            except Exception:
                pass
        else:
            try:
                w.overrideredirect(True)
            except Exception:
                pass
    def taskbar(self,window):#让无边框窗口显示到系统任务栏/程序坞/面板:win清理窗口风格恢复按钮;linux保持普通窗口去装饰;mac的Dock图标属应用级自动显示
        if IS_WINDOWS and windll is not None:
            self._win_show_in_taskbar(window)
            try:#重新映射一次,让上面的窗口风格生效(保留原Windows逻辑)
                window.wm_withdraw()
                window.wm_deiconify()
            except Exception:
                pass
            App_icon.reapply(window)#重映射后任务栏按钮是新生成的,再贴一次图标(句柄复用,不会泄漏)
        elif IS_LINUX:
            try:
                window.overrideredirect(False)
                self._x11_undecorated(window)
                window.wm_withdraw()
                window.wm_deiconify()#重映射让去装饰状态生效(WM在窗口映射时读取_MOTIF_WM_HINTS)
            except Exception:
                pass
        # darwin(macOS):Dock图标属于应用本身自动显示,overrideredirect无边框窗口无需额外处理
    def minimize_click(self):#最小化按钮:win需要临时去掉无边框再iconify,之后从任务栏点图标还原;mac/linux直接交给系统最小化
        w=self.window
        if IS_WINDOWS:
            try:
                w.withdraw()
            except Exception:
                pass
            try:
                w.overrideredirect(False)
            except Exception:
                pass
            try:
                w.iconify()
            except Exception:
                pass
            self.Set_the(2)
        else:
            try:
                w.iconify()
            except Exception:
                pass
    def Set_the(self,Set_the):#点击任务栏/程序坞图标还原窗口后(<Map>事件):重新设成无边框并恢复任务栏显示
        if self.Set_thes==1:#设定只可以循环一次
            self.frameless()#win恢复overrideredirect无边框;linux保持去装饰普通窗口
            self.window.after(getattr(self,'_set_the_after',100), lambda: self.taskbar(self.window))#恢复任务栏
            self.Set_thes=0#设定只可以循环一次
        elif Set_the==2:#得到一次机会进行下一次
            self.Set_thes=1



def Search_copy(window, _input):#复制输入框里选中的内容(没有选中就什么都不做)
    try:
        window.clipboard_append(_input.get()[_input.index("sel.first"):_input.index("sel.last")])
    except Exception:
        pass


def Search_cut(window, _input):#剪切输入框里选中的内容
    try:
        window.clipboard_clear()
        window.clipboard_append(_input.get()[_input.index("sel.first"):_input.index("sel.last")])
        _input.delete(_input.index("sel.first"),_input.index("sel.last"))
    except Exception:
        pass


def Search_paste(window, _input):#粘贴:有选中就先删掉选中再插,没有选中就直接插到光标处
    try:
        try:
            _input.delete(_input.index("sel.first"),_input.index("sel.last"))
            _input.insert(_input.index(tk.INSERT),window.clipboard_get())
        except Exception:
            _input.insert(_input.index(tk.INSERT),window.clipboard_get())
    except Exception:
        pass
