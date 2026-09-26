# -*- coding: utf-8 -*-
"""左侧 12 项导航(从 VG_video 里拆出)。

    1..11 是同一套模板(常态 #2A2A31 / 选中 #131824),只差文字和纵坐标,循环生成;
    第 12 项"加入组织"单独处理(点击打开加群链接)。

    build_left_nav(main)   建好全部导航按钮,并登记进 state.nav_buttons[序号]
"""
from tkinter import Label, PhotoImage, CENTER
from webbrowser import open_new

import model.state as state
from view.layout import nav_font, nav_place_kw, nav_item_size
from view.widgets.nav import nav_button


def build_left_nav(s):
    """建左侧导航;控件统一登记到 state.nav_buttons,键就是 1..12。"""


    _left_blank=PhotoImage(file='')#空图:原来每次进出/点击都新建一张,白堆 Tk 图片对象,统一用一张
    _left_font=nav_font(s.window)
    _left_items=[("精选",2),("动画",4),("电影",6),("综艺",8),("动漫",10),("直播",12),("下载",14),("历史",16),("旅游",18),("游戏",20),("育儿",22)]
    def _left_paint(n,bg):#给第 n 项换底色并清掉图标
        _w=nav_button(n)
        if _w is not None:
            _w.configure(bg=bg,image=_left_blank)
    def _left_leave(n):#离开:不是当前选中的那一项就恢复底色
        if state.current_page!=n:
            _left_paint(n,'#2A2A31')
    def _left_click(n):#点击切页:记录目标页并通知轮播线程重启
        if state.current_page!=n:
            state.target_page=n
            state.carousel_stop=1
    def _left_uncolor_prev(n):#把上一个被选中的项恢复底色
        if state.current_page!=n:
            _left_paint(state.current_page,"#2A2A31")
    for _i,(_left_text,_left_rely) in enumerate(_left_items,1):
        _left_wid,_left_hei=nav_item_size(s.window)
        _left_w=Label(s.window,text='    '+_left_text,width=_left_wid,height=_left_hei,bg=("#131824" if _i==1 else "#2A2A31"),fg="#BEBFBF",image=_left_blank,compound=CENTER,font=_left_font,cursor="hand2",anchor = 'w')
        _left_w.place(**nav_place_kw(s.window,_left_rely))
        state.nav_buttons[_i]=_left_w#Left_option_at() 就是按这个名字取控件
        _left_w.bind("<Leave>",lambda *e,n=_i:_left_leave(n))#离开时候变回,如果当前选中就是这个，那就不变
        _left_w.bind("<Enter>",lambda *e,w=_left_w:w.configure(bg='#131824',image=_left_blank))#进入时变色
        _left_w.bind("<Button-1>",lambda *e,n=_i:_left_click(n))#最初创建的先执行
        _left_w.bind("<Button-1>",lambda *e,w=_left_w:w.configure(bg='#131824',image=_left_blank),"+")
        _left_w.bind("<Button-1>",lambda *e,n=_i:_left_uncolor_prev(n),'+')#把上一个变色的变回原来的色
        _left_w.bind("<Button-1>",s.Page_switching,"+")#后来创建的后执行
        _left_w.bind("<Button-1>",lambda *e,w=_left_w:w.configure(bg='#131824',image=_left_blank),'+')#点击变色
    _join_wid,_join_hei=nav_item_size(s.window)
    state.nav_buttons[12]=Label(s.window,text='  加入组织',width=_join_wid,height=_join_hei,bg="#34343D",fg="#BEBFBF",image=PhotoImage(file=''),compound=CENTER,font=nav_font(s.window), cursor="hand2",anchor = 'w')
    state.nav_buttons[12].place(**nav_place_kw(s.window,24))
    state.nav_buttons[12].bind("<Button-1>",lambda *Left_option_12vg:open_new(""))
    state.nav_buttons[12].bind("<Leave>",lambda *Left_option_12vg:state.nav_buttons[12].configure(fg='#BEBFBF',image=PhotoImage(file='')))#离开时候变回
    state.nav_buttons[12].bind("<Enter>",lambda *Left_option_12vg:state.nav_buttons[12].configure(fg='#FF5C38',image=PhotoImage(file='')))#进入时变色
