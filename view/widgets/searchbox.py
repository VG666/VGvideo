# -*- coding: utf-8 -*-
"""搜索框构件(从 VG_video 里拆出)。

原来是同一段代码在主窗口里被抄了三遍(启动、还原、最大化),
三份只差输入框宽度;现在收成一个函数,主窗口只管调用。

    Search = build_search_box(main, input_relwidth=0.67)
    返回值是那块画布;同时会把下面这些挂到主窗口上:
        main.Search_input            输入框
        main.Search_input_master     画布本身(定位提示框要用)
        main.Search_confirmation     圆角按钮多边形
        main.Search_input_button_2   右键菜单(撤销/全选/复制/剪切/粘贴)

尺寸一律不写死:画布宽按窗口宽、画布高按窗口高算,框内的留白/圆角/字号再由
画布高推算(算式集中在 view/layout.py),所以屏幕大小、分辨率怎么变比例都一致。
"""
import tkinter as tk
from tkinter import Canvas, Entry, Menu

import model.state as state
from view.chrome import Search_copy, Search_cut, Search_paste
from view.layout import (searchbox_width, searchbox_height, searchbox_metrics,
                         searchbox_cover_x, searchbox_text_pos,
                         title_center_y, input_place_kw, SEARCHBOX_RELX)


def build_search_box(s, input_relwidth=0.67):
    """在 s.window 上建一个搜索框,返回画布控件。"""


    _h=searchbox_height(s.window)#画布高:框内留白、圆角、字号都从它推算(见 view/layout.py)
    _m=searchbox_metrics(_h)
    Search=Canvas(s.window,width=searchbox_width(s.window),height=_h,bd=0,highlightthickness=0)
    Search.place(relx=SEARCHBOX_RELX,y=title_center_y(s.left_message_2,_h))#纵向与标题条文字块居中对齐
    x1, y1, x2, y2, radius=_m["pad"], _m["pad"], int(Search["width"]), _h, _m["radius"]
    points=[x1+radius, y1,
              x1+radius, y1,
              x2-radius, y1,
              x2-radius, y1,
              x2, y1,
              x2, y1+radius,
              x2, y1+radius,
              x2, y2-radius,
              x2, y2-radius,
              x2, y2,
              x2-radius, y2,
              x2-radius, y2,
              x1+radius, y2,
              x1+radius, y2,
              x1, y2,
              x1, y2-radius,
              x1, y2-radius,
              x1, y1+radius,
              x1, y1+radius,
              x1, y1]#定位位置
    Search.configure(background=state.style)#更改背景颜色
    s.Search_confirmation=Search.create_polygon(points,None, smooth=True, fill="#44444F")#画出圆角矩形,用于按钮
    x1, y1, x2, y2, radius=_m["pad"], _m["pad"], searchbox_cover_x(int(Search["width"])), _h, _m["radius"]
    points=[x1+radius, y1,
              x1+radius, y1,
              x2-radius, y1,
              x2-radius, y1,
              x2, y1,
              x2, y1+radius,
              x2, y1+radius,
              x2, y2-radius,
              x2, y2-radius,
              x2, y2,
              x2-radius, y2,
              x2-radius, y2,
              x1+radius, y2,
              x1+radius, y2,
              x1, y2,
              x1, y2-radius,
              x1, y2-radius,
              x1, y1+radius,
              x1, y1+radius,
              x1, y1]#定位位置
    Search.create_polygon(points,None, smooth=True, fill="#393942")#画出圆角矩形,仅仅用于覆盖好看
    Search.create_rectangle(_m["occluder_x"], _m["pad"], int(Search["width"])//12*8,_h-1,width=0,fill="#393942")#触发优化，因为在画布之上所有控件都不能作为遮挡,鼠标放到一个画布画出的东西之上,只能再画一个作为遮挡
    s.Search_input_button_2=Menu(Search, tearoff=False,bg="#FFFFFF",fg="#5C5C5C",activebackground="#E6E6E6",activeforeground="#5C5C5C")
    s.Search_input_button_2.add_command(label="撤销（z）",command=lambda:s.Control_zy(90))
    s.Search_input_button_2.add_command(label="全选（a）",command=lambda:s.Search_input.selection_range(0, len(s.Search_input.get())))
    s.Search_input_button_2.add_command(label="复制（c）",command=lambda:Search_copy(s.window,s.Search_input))
    s.Search_input_button_2.add_command(label="剪切（z）",command=lambda:Search_cut(s.window,s.Search_input))
    s.Search_input_button_2.add_command(label="粘贴（z）",command=lambda:Search_paste(s.window,s.Search_input))
    s.Search_input=Entry(Search,bg="#393942",bd=0,font=("微软雅黑",(-1*_h//10*4)),fg="#BABABA",exportselection=0,highlightbackground="#FFFFFF")#输入框
    s.Search_input.insert(tk.END,s.Search_input_text)
    s.Search_input_master=Search
    s.Search_input.place(**input_place_kw(Search,input_relwidth))
    s.Search_input.bind("<Return>",lambda *Search_confirmations:s.Search())#回车启动搜索
    s.Search_input.bind('<FocusIn>',s.FocusIn)#获取焦点,用于做提示,同时用于修复官方所带的一个bug
    s.Search_input.bind('<FocusOut>',s.FocusOut)#失去焦点,用于取消状态
    s.Search_input.bind_all('<Control-z>', s.Control_zy)#快捷键
    s.Search_input.bind_all('<Control-y>', s.Control_zy)#快捷键
    _text_x,_text_y=searchbox_text_pos(int(Search["width"]),_h,input_relwidth)#按钮文字位置:按钮可见区正中(算法见 view/layout.py)
    Search_text=Search.create_text(_text_x,_text_y,text="全网搜",font=("Verdana",_m["button_font"],"bold"),fill="#FF5C38")#按钮文字(靠 anchor 居中,末尾不再垫空格凑位置)
    Search.tag_bind(s.Search_confirmation,"<Enter>",lambda *Search_confirmations:Search.itemconfig(s.Search_confirmation,fill="#FF5246"))#鼠标进入按钮,文字背色改变
    Search.tag_bind(s.Search_confirmation,"<Leave>",lambda *Search_confirmations:Search.itemconfig(s.Search_confirmation,fill="#44444F"))#鼠标离开按钮,文字背景色变回
    Search.tag_bind(s.Search_confirmation,"<Enter>",lambda *Search_confirmations:Search.itemconfig(Search_text,fill="#FFFFFF"),"+")#鼠标进入按钮,文字变色
    Search.tag_bind(s.Search_confirmation,"<Leave>",lambda *Search_confirmations:Search.itemconfig(Search_text,fill="#FF5C38"),"+")#鼠标离开按钮,文字鼠标背景色变回
    Search.tag_bind(s.Search_confirmation,"<Enter>",lambda *Search_confirmations:Search.configure(cursor="hand2"),"+")#鼠标放在按钮之上,鼠标在画布之上就改为手指状
    Search.tag_bind(s.Search_confirmation,"<Leave>",lambda *Search_confirmations:Search.configure(cursor="arrow"),"+")#鼠标离开按钮,鼠标在画布上就恢复最初的图案
    Search.tag_bind(Search_text,"<Enter>",lambda *Search_confirmations:Search.itemconfig(s.Search_confirmation,fill="#FF5246"))#鼠标放在按钮文字之上,按钮改变颜色
    Search.tag_bind(Search_text,"<Leave>",lambda *Search_confirmations:Search.itemconfig(s.Search_confirmation,fill="#44444F"))#鼠标离开按钮文字之上,按钮颜色变回
    Search.tag_bind(Search_text,"<Enter>",lambda *Search_confirmations:Search.itemconfig(Search_text,fill="#FFFFFF"),"+")#鼠标放在按钮文字之上,文字改变颜色
    Search.tag_bind(Search_text,"<Leave>",lambda *Search_confirmations:Search.itemconfig(Search_text,fill="#FF5C38"),"+")#鼠标离开按钮文字之上,文字颜色变回
    Search.tag_bind(Search_text,"<Leave>",lambda *Search_confirmations:Search.configure(cursor="arrow"),"+")#鼠标放在按钮文字之上,鼠标在画布之上就改为手指状
    Search.tag_bind(Search_text,"<Enter>",lambda *Search_confirmations:Search.configure(cursor="hand2"),"+")#鼠标离开按钮文字,鼠标在画布上就恢复最初的图案
    Search.tag_bind(s.Search_confirmation,"<Button-1>",lambda *Search_confirmations:s.Search())
    Search.tag_bind(Search_text,"<Button-1>",lambda *Search_confirmations:s.Search(),"+")
