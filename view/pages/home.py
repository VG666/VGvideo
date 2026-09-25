# -*- coding: utf-8 -*-
"""首页:轮播大图 + "大家在看" + 四个推荐位(从 main.py 拆出)

    The_home_page(vgFrames, style, 页码)   首页整块内容的搭建

轮播/推荐位的画图逻辑在 view.widgets.carousel.py,本模块只负责"摆位置、起线程"。
注意 style / frequency 是本构造函数的参数(不是全局),所以这里按参数用。
"""
from threading import Thread
from tkinter import Frame, Label, PhotoImage, CENTER

import model.state as state
from model.api import _fetch_rotation_data
from view.widgets.carousel import load_elect_image, carousel_loop


class The_home_page(object):
    def __init__(self,vgFrames,style,frequency):
        # 旧逻辑解析数据源站点页面 HTML 里的"重磅推荐"区块,改版后已失效;
        # 现改为走新版频道页数据接口取线上真实轮播海报(getPage->pc_carousel)。
        state.carousel_posters,Rotation_data_2,state.recommend_pages,state.recommend_posters=_fetch_rotation_data(frequency)
        self.vgFrames=vgFrames
        self.vgFrames.configure(bg=style)#更改背景颜色
        state.carousel_label=Label(self.vgFrames,text="等待加载...              ",compound=CENTER,width=self.vgFrames["width"]-int(self.vgFrames["width"]//120*6),image=PhotoImage(file=''),font=("Comic Sans MS",-30,"bold"), cursor="watch")#image=PhotoImage(file='')这一行在代码中很常出现很多人搞不懂为什么,其实用了图片的标签跟不用图片的标签是不一样的,不用图片100就能达到的长度,用了图片需要1000才可以达到,这也使得程序更加精细,所以我加入的原因就是因为这个
        state.carousel_label.place(x=0,y=0,relheight=0.48,relwidth=0.8)
        Home_rotation_right=Frame(self.vgFrames,width=int(self.vgFrames["width"]//120*43),bg="#1C1E26",highlightthickness=0)#创建一个精度高的，主要是旁边那块黑色
        Home_rotation_right.place(relx=1.25,relwidth=1,y=0,relheight=0.48,anchor='n')
        Home_rotation_right_Label=Label(Home_rotation_right,text=" 大家在看",bg="#1C1E26",fg="#818182",font=("Comic Sans MS",self.vgFrames["width"]//52*-1,"bold"),anchor = 'w')#这里设置主题标签
        Home_rotation_right_Label.place(x=0,rely=0.02,anchor='nw')
        #由于特殊原因省下内存之类的需要用标签直接搞
        font_size=self.vgFrames["width"]//65*-1
        state.trending_labels[1]=Label(Home_rotation_right,text="         "+Rotation_data_2[0],fg="#818182",bg="#1C1E26",font=("Comic Sans MS",font_size),anchor = 'w')
        state.trending_labels[1].place(x=0,rely=0.12,relwidth=1,anchor='nw')
        state.trending_labels[2]=Label(Home_rotation_right,text="         "+Rotation_data_2[1],fg="#818182",bg="#1C1E26",font=("Comic Sans MS",font_size),anchor = 'w')
        state.trending_labels[2].place(x=0,rely=0.25,relwidth=1,anchor='nw')
        state.trending_labels[3]=Label(Home_rotation_right,text="         "+Rotation_data_2[2],fg="#818182",bg="#1C1E26",font=("Comic Sans MS",font_size),anchor = 'w')
        state.trending_labels[3].place(x=0,rely=0.38,relwidth=1,anchor='nw')
        state.trending_labels[4]=Label(Home_rotation_right,text="         "+Rotation_data_2[3],fg="#818182",bg="#1C1E26",font=("Comic Sans MS",font_size),anchor = 'w')
        state.trending_labels[4].place(x=0,rely=0.51,relwidth=1,anchor='nw')
        state.trending_labels[5]=Label(Home_rotation_right,text="         "+Rotation_data_2[4],fg="#818182",bg="#1C1E26",font=("Comic Sans MS",font_size),anchor = 'w')
        state.trending_labels[5].place(x=0,rely=0.64,relwidth=1,anchor='nw')
        state.trending_labels[6]=Label(Home_rotation_right,text="         "+Rotation_data_2[5],fg="#818182",bg="#1C1E26",font=("Comic Sans MS",font_size),anchor = 'w')
        state.trending_labels[6].place(x=0,rely=0.77,relwidth=1,anchor='nw')
        state.trending_labels[7]=Label(Home_rotation_right,text="         "+Rotation_data_2[6],fg="#818182",bg="#1C1E26",font=("Comic Sans MS",font_size),anchor = 'w')
        state.trending_labels[7].place(x=0,rely=0.90,relwidth=1,anchor='nw')

        del Rotation_data_2,font_size#变量删除释放内存
        state.elect_labels[1]=Label(self.vgFrames,image=PhotoImage(file=''),bg=style)
        state.elect_labels[1].place(relx=0,rely=0.49,relheight=0.49,relwidth=1/5)
        state.elect_labels[2]=Label(self.vgFrames,image=PhotoImage(file=''),bg=style)
        state.elect_labels[2].place(relx=0.07+1/5,rely=0.49,relheight=0.49,relwidth=1/5)
        state.elect_labels[3]=Label(self.vgFrames,image=PhotoImage(file=''),bg=style)
        state.elect_labels[3].place(relx=0.93-2/5,rely=0.49,relheight=0.49,relwidth=1/5)
        state.elect_labels[4]=Label(self.vgFrames,image=PhotoImage(file=''),bg=style)
        state.elect_labels[4].place(relx=1-1/5,rely=0.49,relheight=0.49,relwidth=1/5)
        if frequency<9:
            _elect1_url_index,_elect1_page_index=4,4
        else:
            _elect1_url_index,_elect1_page_index=len(state.recommend_pages)-2,len(state.recommend_pages)-2
        Elect1s=Thread(target=load_elect_image,args=(state.elect_labels[1],_elect1_url_index,_elect1_page_index,self.vgFrames["width"],self.vgFrames["height"],state.carousel_label["height"],"image_1"))
        Elect1s.daemon = True
        Elect1s.start()
        if frequency<9:
            _elect2_url_index,_elect2_page_index=1,1
        else:
            _elect2_url_index,_elect2_page_index=3,3
        Elect2s=Thread(target=load_elect_image,args=(state.elect_labels[2],_elect2_url_index,_elect2_page_index,self.vgFrames["width"],self.vgFrames["height"],state.carousel_label["height"],"image_2"))
        Elect2s.daemon = True
        Elect2s.start()
        Elect3s=Thread(target=load_elect_image,args=(state.elect_labels[3],2,2,self.vgFrames["width"],self.vgFrames["height"],state.carousel_label["height"],"image_3"))
        Elect3s.daemon = True
        Elect3s.start()
        if frequency<9:
            _elect4_url_index,_elect4_page_index=3,3
        else:
            _elect4_url_index,_elect4_page_index=len(state.recommend_pages)-1,len(state.recommend_pages)-1
        Elect4s=Thread(target=load_elect_image,args=(state.elect_labels[4],_elect4_url_index,_elect4_page_index,self.vgFrames["width"],self.vgFrames["height"],state.carousel_label["height"],"image_4"))
        Elect4s.daemon = True
        Elect4s.start()
        try:#轮播尺寸必须取 Frame 的配置宽高:这里 vgFrame 刚创建还没完成布局,winfo_width()/winfo_height() 还是 1,
            #会让缩放参数算成 0(Picture_transcoding 中 min(0/w,0/h)=0),resize((0,0)) 抛错被吞→轮播线程直接退出(切页后不刷新)
            _carousel_w=int(float(self.vgFrames["width"]))
            _carousel_h=int(float(self.vgFrames["height"]))
        except Exception:#取不到配置值时再退回实际渲染尺寸
            _carousel_w=self.vgFrames.winfo_width()
            _carousel_h=self.vgFrames.winfo_height()
        Guardian_carousel=Thread(target=carousel_loop,args=(_carousel_w,_carousel_h))
        Guardian_carousel.daemon = True
        Guardian_carousel.start()#主要是因为定时器有bug不可以直接用，不然也不会开这个来运行切换轮播图
