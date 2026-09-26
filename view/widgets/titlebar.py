# -*- coding: utf-8 -*-
"""标题栏三键 + 菜单(从 VG_video 里拆出)。

    最小化 / 最大化 / 关闭 / ≡ 菜单(播放本地文件、设置下载位置、关于、退出)

    build_window_controls(main)   把这一排按钮摆到主窗口右上角并绑好事件
"""
from os import _exit
from threading import Thread
from tkinter import Frame, Label, Menu, filedialog
import tkinter.messagebox

import ToolTips
import model.state as state
from model.paths import _save_download_dir
from view.layout import (scaled_font, control_pad, title_item_y, TITLE_CONTROL_OFFSET,
                         CONTROL_RELX, CONTROL_FONT_DIV_MENU, CONTROL_FONT_DIV_MINIMIZE,
                         CONTROL_FONT_DIV_MAXIMIZE, CONTROL_FONT_DIV_CLOSE)
from controller.entry import VGvideo


def build_window_controls(s):
    """在主窗口右上角摆出 菜单 / 最小化 / 最大化 / 关闭。"""


    High_control=title_item_y(s.left_message_2,TITLE_CONTROL_OFFSET)#纵坐标算式统一在 view/layout.py
    control=Frame(s.window,bg=state.style)#创建一个容器，在利用表格布局，使得菜单缩小删除三个按钮平行
    control.place(relx=CONTROL_RELX, y=High_control*0.8)
    minimize=Label(control, text='_',bg=state.style,fg="#818182",font=scaled_font(s.window,CONTROL_FONT_DIV_MINIMIZE), cursor="hand2")#设置最小化按钮使用标签输入文字实现所以把背景调成当前颜色背景字体调整#FFFFFF
    minimize.grid(row=1, column=2, padx=control_pad(s.window))
    minimize.bind("<Button-1>",lambda *minimizevg:s.minimize_click())#最小化到任务栏(win走无边框还原技巧,mac/linux交给系统)
    minimize.bind("<Leave>",lambda *minimizevg:minimize.configure(fg="#818182"))#离开时候变回
    minimize.bind("<Enter>",lambda *minimizevg:minimize.configure(fg="#FF5C38"))#进入时变色
    s.Maximize=Label(control, text='☐',bg=state.style,fg="#818182",font=scaled_font(s.window,CONTROL_FONT_DIV_MAXIMIZE), cursor="hand2")#设置最大化按钮使用标签输入文字实现所以把背景调成当前颜色背景字体调整#FFFFFF
    s.Maximize.grid(row=1, column=3,pady=control_pad(s.window),padx=control_pad(s.window))
    s.Maximize.bind("<Leave>",lambda *menuvg:s.Maximize.configure(fg="#818182"))#离开时候变回
    s.Maximize.bind("<Enter>",lambda *menuvg:s.Maximize.configure(fg="#FF5C38"))#进入时变色
    s.Maximize.bind("<Button-1>",s.Maximizevent,"+")
    no=Label(control, text='×',fg="#818182",bg=state.style,font=scaled_font(s.window,CONTROL_FONT_DIV_CLOSE,family="PMingLiU-ExtB"), cursor="hand2")#设置删除按钮使用标签输入文字实现所以把背景调成当前颜色背景字体调整#FFFFFF
    no.grid(row=1, column=4,padx=control_pad(s.window))
    no.bind("<Button-1>",lambda *no: _exit(0),"+")#关闭窗口destroy代表关闭
    no.bind("<Leave>",lambda *novg:no.configure(fg="#818182"))#离开时候变回
    no.bind("<Enter>",lambda *novg:no.configure(fg="#FF5C38"))#进入时变色
    Menuvg=Label(control, text='≡',fg="#818182",bg=state.style,font=scaled_font(s.window,CONTROL_FONT_DIV_MENU,bold=False), cursor="hand2")#设置删除按钮使用标签输入文字实现所以把背景调成当前颜色背景字体调整#FFFFFF
    Menuvg.grid(row=1, column=1, padx=control_pad(s.window))
    Menuvg.bind("<Button-1>",lambda menuvg: menu.post(menuvg.x_root,menuvg.y_root),"+")#关闭窗口destroy代表关闭
    Menuvg.bind("<Leave>",lambda *menuvg:Menuvg.configure(fg="#818182"))#离开时候变回
    Menuvg.bind("<Enter>",lambda *menuvg:Menuvg.configure(fg="#FF5C38"))#进入时变色
    menu=Menu(Menuvg, tearoff=False,bg="#FFFFFF",fg="#5C5C5C",activebackground="#E6E6E6",activeforeground="#5C5C5C")
    def _play_local_file():#选本地文件播放(弹选择框+起播放器,整体放后台线程,别卡界面)
        try:
            filename=filedialog.askopenfilenames(title=u'选择文件')[0]#选择文件
        except Exception:#用户取消时返回空,取 [0] 会报错,直接忽略
            return
        if filename!="":#判断是否有没有选择
            VGvideo(f'video.exe 1 "{filename}"')#传入参数，进行视频播放
    menu.add_command(label="播放本地文件",command=lambda:Thread(target=_play_local_file,daemon=True).start())
    def _choose_download_dir():#选文件下载位置,记到 config.json 的 path.download_dir
        file=filedialog.askdirectory(title=u'文件下载地址')#选择文件夹
        if file!="":#判断是否有没有选择
            _save_download_dir(file)#写进 config.json 的 path.download_dir(与接口层读的是同一份)
    menu.add_command(label="文件下载位置",command=_choose_download_dir)
    menu.add_command(label="关于",command=lambda *menuvg:tkinter.messagebox.showinfo('关于','开发者QQ:1684512896'))
    alpha_menu=Menu(menu,tearoff=False,bg="#FFFFFF",fg="#5C5C5C",activebackground="#E6E6E6",activeforeground="#5C5C5C")
    def _set_alpha(level):#整窗透明度:主窗口立即生效,之后新开的播放器窗口按同一档继承(state.window_alpha)
        try:
            state.window_alpha=level
            s.apply_alpha(level)
        except Exception:
            pass
    for _a_label,_a_level in (("不透明",1.0),("95%",0.95),("90%",0.9),("80%",0.8),("70%",0.7)):
        alpha_menu.add_command(label=_a_label,command=lambda level=_a_level:_set_alpha(level))
    menu.add_cascade(label="窗口透明度",menu=alpha_menu)
    menu.add_command(label="退出",command=lambda *menuvg: _exit(0))
    ToolTips.ToolTip(s.Maximize, msg="最大化",follow=True,delay=0.3)
    ToolTips.ToolTip(minimize, msg="最小化",follow=True,delay=0.3)#这是一个本地导入的包,同文件夹里面有,用于最小化按钮提示
    ToolTips.ToolTip(no, msg="关闭",follow=True, delay=0.3)#这是一个本地导入的包,同文件夹里面有,用于删除按钮提示
    ToolTips.ToolTip(Menuvg, msg="菜单",follow=True,delay=0.3)#这是一个本地导入的包,同文件夹里面有,用于菜单按钮提示
