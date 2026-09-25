# -*- coding: utf-8 -*-
"""主窗口 / 启动页 —— VG_video(从 main.py 拆出)

    VG_video().start()   建主窗口、装标题栏三键与左侧导航、挂好首页,然后进入 mainloop

这个类只保留"窗口骨架 + 事件分发 + 页面切换":
    搜索框      见 view/widgets/searchbox.py
    标题栏三键  见 view/widgets/titlebar.py
    左侧导航    见 view/widgets/leftnav.py
    热词下拉    见 view/widgets/suggest.py
    五个内容页  见 view/pages/{home,search,history,download,live}.py
所有跨模块共享的状态统一放在 state.py。
"""
import sys
from threading import Thread
from tkinter import (Tk, Toplevel, Canvas, Frame, Label, Entry, Menu, PhotoImage,
                     filedialog, END, CENTER)

from PIL import Image, ImageTk

import model.state as state
import ToolTips
from model.paths import IS_WINDOWS, windll, _data_path, application_path
from view.image import Picture_transcoding, _safe_attributes
from view.icons import App_icon
from view.chrome import Window_chrome, Search_copy, Search_cut, Search_paste
from view.layout import (new_content_frame, title_bar_width, title_bar_height,
                         title_logo_size, title_logo_font, title_logo_image_size,
                         RELAYOUT_HOME, RELAYOUT_WIDE)
from model.api import search_hot_words
from controller.entry import VGvideo
from view.widgets.nav import nav_button
from view.widgets.carousel import carousel_loop
from view.widgets.searchbox import build_search_box
from view.widgets.titlebar import build_window_controls
from view.widgets.leftnav import build_left_nav
from view.widgets.suggest import focus_in, focus_out
from view.pages.home import The_home_page
from view.pages.search import Searchs
from view.pages.live import live_broadcast
from view.pages.history import history
from view.pages.download import download

try:
    from windnd import hook_dropfiles
except Exception:
    def hook_dropfiles(window, func):      # 非 Windows 没有桌面拖放,留个空实现
        return None
try:
    import max_win                        # 仅 Windows 可用:取任务栏工作区做最大化
except Exception:
    max_win = None


class VG_video(Window_chrome):#启动页面的类
    def start(s):
        s.Set_thes=1
        state.style="#303038"
        hot_words=search_hot_words()#搜索推荐词,数据源统一在 search_hot_words()(见文件头部)
        s.Search_input_text=(hot_words[0] if hot_words else "")#搜索框默认提示词取第一个热词
        s.input_get=[[""]]
        s.download=False
        s.zoomednormal_2=0
        s.window=Tk()
        if IS_WINDOWS and windll is not None:#Windows才能用shcore接口设DPI;其他系统用Tk默认缩放
            try:
                windll.shcore.SetProcessDpiAwareness(1)
                ScaleFactor=windll.shcore.GetScaleFactorForDevice(0)
                s.window.tk.call('tk', 'scaling', ScaleFactor/75)
            except Exception:
                pass
        s.recommend=Toplevel()
        s.recommend.withdraw()
        state.main_window=s#登记主窗口实例:推荐位点击、按参数启动播放器都要用它(拆分时漏了这行,导致点击推荐位报 NoneType)
        s.frameless()#去掉标准控件边框(各系统无边框策略不同,见Window_chrome.frameless)
        s.window.after(100, lambda: s.taskbar(s.window))#恢复任务栏显示
        _safe_attributes(s.window,("-transparentcolor","blue"))#透明色仅Windows支持
        s.window.title("VG视频")#设置标题名
        s.window.geometry(f'{(s.window.winfo_screenwidth()-s.window.winfo_screenwidth()//4)}x{(s.window.winfo_screenheight()-s.window.winfo_screenheight()//6)}+{(s.window.winfo_screenwidth()-(s.window.winfo_screenwidth()-s.window.winfo_screenwidth()//4))//2}+{(s.window.winfo_screenheight()-(s.window.winfo_screenheight()-s.window.winfo_screenheight()//6))//2}')
        s.window.configure(background = state.style)#更改背景颜色
        s.edge_bg=state.style#8组边缘缩放热区刷成窗口底色:不带颜色、不穿透,自然也就没有"蓝边框"(见 view/chrome.py EDGE_BG)
        s.apply_alpha()#按 ≡ 菜单里选过的整窗透明度设置生效(默认 1.0 不透明)

        App_icon.apply_default(s.window)#主窗口图标:标题栏+任务栏,后续新建的Toplevel自动继承
        s.window.update()
        s.wh1=s.window.winfo_width()
        s.wh2=s.window.winfo_height()
        s.new_x=s.window.winfo_x()
        s.new_y=s.window.winfo_y()
        s.Maximize_ty=True
        def _drop_play(*file):#拖进来的文件:逐个丢到后台线程里播放
            for i in file[0]:
                try:
                    i='video.exe 1 "'+i.decode()+'" 4'
                except Exception:
                    i='video.exe 1 "'+i.decode('gbk')+'" 4'
                play=Thread(target=VGvideo,args=(i,))
                play.daemon = True
                play.start()#执行
        hook_dropfiles(s.window,func=_drop_play)
        move=Label(s.window,width=s.window.winfo_width(),height=title_bar_height(s.window),bg=state.style,highlightthickness=0,image=PhotoImage(file=''))
        move.pack()
        move.bind("<Button-1>",s.mobile_2)#绑定移动函数
        move.bind("<B1-Motion>",s.mobile_1)#绑定移动函数
        move.bind("<ButtonRelease-1>",s.mobile_3)
        s.left_message_1=Label(s.window,width=title_bar_width(s.window),bg="#2A2A31",image=PhotoImage(file=''))
        s.left_message_1.place(x=0,y=0,relheight=1)
        image_data=App_icon.image()#取程序图标(ico/logo.ico),载入管理器
        w, h = image_data.size#获取当前宽高
        _logo_w,_logo_h=title_logo_size(s.window)#"VG视频"文字块宽高
        _logo_img=title_logo_image_size(s.window)#图标边长(与文字块不是同一个算式,原样保留)
        image_data=Picture_transcoding(w, h, _logo_img, _logo_img, image_data)#将图片大小转化为可适应当前大小的尺寸
        state.logo_image=ImageTk.PhotoImage(image_data)#转化为控件使用对象
        s.left_message_2=Label(s.window,text="VG视频",width=_logo_w,height=_logo_h,image=state.logo_image,compound='left',bg="#2A2A31",font=title_logo_font(s.window),fg="#FFFFFF")#这里是右上角那个图片和字
        s.left_message_2.place(x=0,y=0)
        s.left_message_2.bind("<B1-Motion>",s.mobile_1)#绑定移动函数
        s.left_message_2.bind("<Button-1>",s.mobile_2)#绑定移动函数
        s.left_message_2.bind("<ButtonRelease-1>",s.mobile_3)
        Search=build_search_box(s, 0.67)#搜索框:圆角画布+输入框+右键菜单(见 view/widgets/searchbox.py)
        build_window_controls(s)#最小化/最大化/关闭/菜单(见 view/widgets/titlebar.py)
        s.window.update()
        #左侧导航 1..11 是同一套模板(常态 #2A2A31 / 选中 #131824),只差文字和纵坐标,循环生成,12 单独处理
        build_left_nav(s)#左侧 12 项导航(见 view/widgets/leftnav.py)
        
        s.edge=[
          [Label(s.window,cursor="sb_h_double_arrow",bg=s.edge_bg,bd=0,highlightthickness=0),Label(s.window,cursor="size_nw_se",bg=s.edge_bg,bd=0,highlightthickness=0)],
          [Label(s.window,cursor="sb_h_double_arrow",bg=s.edge_bg,bd=0,highlightthickness=0),Label(s.window,cursor="size_ne_sw",bg=s.edge_bg,bd=0,highlightthickness=0)],
          [Label(s.window,cursor="sb_v_double_arrow",bg=s.edge_bg,bd=0,highlightthickness=0),Label(s.window,cursor="size_ne_sw",bg=s.edge_bg,bd=0,highlightthickness=0)],
          [Label(s.window,cursor="sb_v_double_arrow",bg=s.edge_bg,bd=0,highlightthickness=0),Label(s.window,cursor="size_nw_se",bg=s.edge_bg,bd=0,highlightthickness=0)]
        ]
        s.display(s.edge)#初始摆放并绑定8组边缘缩放(公共逻辑见Window_chrome.display)
        s.window.bind('<FocusIn>',lambda event:s.FocusIn_edge(s.edge))#获取焦点,用于做提示,同时用于修复官方所带的一个bug
        s.window.bind('<FocusOut>',lambda event:s.FocusOut_edge(s.edge))#失去焦点,用于取消状态
        s.window.update()
        s.vgFrame=new_content_frame(s.window,RELAYOUT_HOME,bg="#303038")#内容区尺寸/定位算式统一在 view/layout.py
        s.The_home_page=Thread(target=The_home_page,args=(s.vgFrame,state.style,1))#多线程载入
        s.The_home_page.daemon = True#守护线程
        s.The_home_page.start()#启动
        s.window.bind('<Map>',lambda *minimizevg:s.Set_the(1))#显示主窗口,因为点击一下其实会触发很多次，所以才需要有一个判断
        s.window.bind('<Map>',lambda *minimizevg:s.window.after(1, lambda: s.window.focus_force()),"+")
        s.window.mainloop()

    def zoomednormal(s,_left=20):
      try:
        if s.zoomednormal_2==0 and "win" in sys.platform:
          geometry=max_win.max_win()
          s.window.geometry(f"{geometry[2]-geometry[0]}x{geometry[3]-geometry[1]}+{geometry[0]}+{geometry[1]}") 
          s.window.update()
          if _left>0:#原来是 after(1,...) 无上限循环:最大化期间每秒上千次 update() 把窗口死死钉在工作区,拖着蓝框跑而窗口不动,松手还会跳位;补几次让铺满生效就够了
            s.window.after(1,lambda:s.zoomednormal(_left-1))
          s.Maximize["text"]="❐"
        else:
          s.zoomednormal_2=1
          s.window.geometry(f"{s.wh1}x{s.wh2}+{s.new_x}+{s.new_y}")
          s.window.update()
          s.Maximize["text"]="☐"
          s.Search_input_master.destroy()
          Search=build_search_box(s, 0.67)#搜索框:圆角画布+输入框+右键菜单(见 view/widgets/searchbox.py)
          s.display(s.edge)
          Guardian_carousel=Thread(target=lambda:carousel_loop(s.vgFrame.winfo_width(),s.vgFrame.winfo_height()))
          Guardian_carousel.daemon = True
          Guardian_carousel.start()
      except:
        pass
    def Maximizevent(s,*event):
      s.recommend.withdraw()
      if s.Maximize_ty:
          s.zoomednormal_1=0
          s.zoomednormal_2=0
          s.wh1=s.window.winfo_width()
          s.wh2=s.window.winfo_height()
          s.new_x=s.window.winfo_x()#把"最大化的那一刻"窗口真实所在的位置也记下来:还原时回到这里,而不是上次拖动留下的记忆值
          s.new_y=s.window.winfo_y()
          s.window.after(1,s.zoomednormal)
          s.hide(s.edge)
          s.window.update()
          s.Search_input_master.destroy()
          Search=build_search_box(s, 0.7)#搜索框:圆角画布+输入框+右键菜单(见 view/widgets/searchbox.py)
      else:
          s.zoomednormal_2=1
          s.window.geometry(f"{s.wh1}x{s.wh2}+{s.new_x}+{s.new_y}")
          s.window.update()
          s.Maximize["text"]="☐"#还原成普通窗口,按钮图标必须跟着回"☐"(原来这条分支漏了,还原后图标还停在❐,看着就像窗口逻辑乱套了)
          s.Search_input_master.destroy()
          Search=build_search_box(s, 0.67)#搜索框:圆角画布+输入框+右键菜单(见 view/widgets/searchbox.py)
          s.display(s.edge)
      Guardian_carousel=Thread(target=lambda:carousel_loop(s.vgFrame.winfo_width(),s.vgFrame.winfo_height()))
      Guardian_carousel.daemon = True
      Guardian_carousel.start()
      s.Maximize_ty=not(s.Maximize_ty)

    def Control_zy(s,event):
      try:
        if event.keycode==90 and len(s.input_get)>=2:
          s.Search_input.delete(0, END)#清空所有东西
          s.Search_input.insert(END,s.input_get[-2][0])
          s.input_get[-1]=[s.input_get[-2][0],s.input_get[-1][0]]
          s.input_get=s.input_get[:-1]
        elif len(s.input_get)>=2:
          if len(s.input_get[-2])==2:
            s.Search_input.delete(0, END)#清空所有东西
            s.Search_input.insert(END,s.input_get[-2][-1])
            s.input_get[-1]=[s.input_get[-2][0]]   
      except:
        if event==90 and len(s.input_get)>=2:
          s.Search_input.delete(0, END)#清空所有东西
          s.Search_input.insert(END,s.input_get[-2][0])
          s.input_get[-1]=[s.input_get[-2][0],s.input_get[-1][0]]
          s.input_get=s.input_get[:-1]
        elif len(s.input_get)>=2:
          if len(s.input_get[-2])==2:
            s.Search_input.delete(0, END)#清空所有东西
            s.Search_input.insert(END,s.input_get[-2][-1])
            s.input_get[-1]=[s.input_get[-2][0]]  
    def Page_switching(s,*Page_switching):
        state.nav_buttons[12].configure(bg="#34343D",image=PhotoImage(file=''))#由于搜索图后再点击改变颜色的机制问题,在这里变回
        s.download=False
        if not(state.target_page!=state.current_page and state.target_page!=6 and state.target_page!=7 and state.target_page!=8):
          state.carousel_stop=state.carousel_stop+1
        if state.target_page!=state.current_page and state.target_page!=6 and state.target_page!=7 and state.target_page!=8:
            s.vgFrame.destroy()
            s.vgFrame=new_content_frame(s.window,RELAYOUT_HOME)
            The_home_page(s.vgFrame,state.style,state.target_page)
        elif state.target_page!=state.current_page and state.target_page==6:
            s.vgFrame.destroy()
            s.vgFrame=new_content_frame(s.window,RELAYOUT_WIDE)
            live_broadcast(s.vgFrame,state.style)
        elif state.target_page!=state.current_page and state.target_page==7:
            s.vgFrame.destroy()
            s.vgFrame=new_content_frame(s.window,RELAYOUT_WIDE)
            nav_button(state.current_page).configure(bg='#2A2A31',image=PhotoImage(file=''))
            state.current_page=state.target_page
            state.nav_buttons[7].configure(bg='#131824',image=PhotoImage(file=''))
            s.vgFrame["bg"]=state.style
            s.download=True
            state.nav_buttons[12].configure(bg="#34343D",image=PhotoImage(file=''))
            download(s.vgFrame,state.style)#下载页:列出下载目录里已下好的视频(见 view/pages/download.py)
        elif state.target_page!=state.current_page and state.target_page==8:
            s.vgFrame.destroy()
            s.vgFrame=new_content_frame(s.window,RELAYOUT_WIDE)
            nav_button(state.current_page).configure(bg='#2A2A31',image=PhotoImage(file=''))
            state.current_page=state.target_page
            state.nav_buttons[8].configure(bg='#131824',image=PhotoImage(file=''))
            s.vgFrame["bg"]=state.style
            s.download=True
            state.nav_buttons[12].configure(bg="#34343D",image=PhotoImage(file=''))
            history(s.vgFrame,state.style)

    def _drag_finished(s):#拖拽结束:把"普通窗口"状态与按钮图标对齐(位置记忆由公共的 mobile_3 写进 new_x/new_y)
        s.zoomednormal_2=1#窗口已不在"铺满"状态
        s.Maximize_ty=True#拖动只可能发生在未最大化的窗口(最大化时被 _drag_locked 挡掉),这里做兜底自愈
        try:
            s.Maximize["text"]="☐"#图标与状态对齐,避免"显示最大化图标其实已经是普通窗口"导致下次点击走错分支
        except Exception:
            pass

    def Search(s):
        s.download=False
        s.recommend.withdraw()
        s.Search_input["fg"]="#FFFFFF"#推荐提示,状态下点搜索,颜色不改变，有点难看，所以改变个颜色
        nav_button(state.current_page).configure(bg="#2A2A31",image=PhotoImage(file=""))
        s.vgFrame.destroy()
        s.vgFrame=new_content_frame(s.window,RELAYOUT_WIDE,on_screen=True)#配置宽高按屏幕尺寸算(原样保留),定位算式见 view/layout.py
        if s.Search_input.get()=="":
          Searchs(s.vgFrame,state.style,1,s.Search_input_text)
        else:
          Searchs(s.vgFrame,state.style,1,s.Search_input.get())
        state.nav_buttons[12].configure(bg="#34343D",image=PhotoImage(file=''))
        state.target_page=12#把当前的改为12,这样点击上次点击过的就不会出错
        state.current_page=12#把把上一次点击的改成12,这样点击上次点击过的就不会出错,但是把上次点击的改回原来的颜色，由于这个机制原来的颜色会改变

    def FocusIn(s, *event):#搜索框热词下拉(界面逻辑见 view/widgets/suggest.py)
        focus_in(s, *event)

    def FocusOut(s, event):#失去焦点(界面逻辑见 view/widgets/suggest.py)
        focus_out(s, event)
