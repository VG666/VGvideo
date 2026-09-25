# -*- coding: utf-8 -*-
"""首页轮播与四个推荐位(从 main.py 拆出)

    load_carousel_image : 单张轮播图加载(优先线上海报,失败回落本地 rotation_local)
    carousel_loop       : 轮播线程主体(首页 / 播放页启动 / 最大化 三处共用)
    load_elect_image    : 首页下方 4 个推荐位拉图并设置(每个推荐位一个线程)

依赖:model.state(共享状态)、model.paths(程序目录)、view.image(等比缩放)、model.api(取图)
"""
import os
from threading import Thread
from time import sleep

from tkinter import PhotoImage
from PIL import Image, ImageTk

import model.state as state
from model.paths import application_path, _download_dir_arg
from view.image import Picture_transcoding
from model.api import fetch_image
from view.widgets.nav import nav_button, trending_label
from view.widgets.episode import style_episode_list

_rotation_local_dir = os.path.join(application_path, "rotation_local")


def _hide_recommend():#点推荐位后把"推荐"浮层收起来(主窗口还没登记就忽略,不让 Tk 回调抛异常)
    try:
        state.main_window.recommend.withdraw()
    except Exception:
        pass


def _open_player(args):
    """打开播放窗口(函数内 import:view.widgets 与 controller.entry 互相引用,必须延迟到调用时)"""
    from controller.entry import VGvideo
    return VGvideo(args)


def load_carousel_image(index):#轮播图图片加载统一入口(index从0开始,表示第几张)
      """先取线上"重磅推荐"真实海报,网络失败再回退本地占位图 rotation_local/1.png..7.png"""
      try:
            if state.carousel_posters and index<len(state.carousel_posters) and state.carousel_posters[index]:
                  return fetch_image(state.carousel_posters[index])
      except Exception:
            pass
      try:
            return Image.open(os.path.join(_rotation_local_dir, "%d.png" % (int(index)+1)))
      except Exception:
            return None



def carousel_loop(vgFrames_width, vgFrames_height):#首页轮播线程主体:zoomednormal/Maximizevent/VG_video.__init__ 三处轮播逻辑统一到这里执行
    sleep(1)
    state.current_page=state.target_page#这里记录一下,当前运行的是第几个页面,如果运行的页面不一样,那就关闭
    vgFrames={}#图方便,不改名,直接创建字典，再传入数据，然后加进去
    vgFrames["width"]=vgFrames_width
    vgFrames["height"]=vgFrames_height
    poster_index=0#循环的时候给他添加,适用于判断当前哪张图片
    poster_cache=[0,1,2,3,4,5,6]#创建一个列表,之后把图片放进去，就不用二次转换了
    state.carousel_stop=state.carousel_stop+1
    Kill_i=state.carousel_stop
    Twice=1#记录一下,将图片列入列表的是否已经完成
    try:
        state.carousel_label.configure(text="等待加载...              ",image=PhotoImage(file=''))#清空当前图片,并恢复文字
    except Exception:
        pass
    try:
        if state.current_page!=12:
            nav_button(state.current_page).configure(bg='#131824',image=PhotoImage(file=''))
    except Exception:
        pass
    try:
        for i in range(7):
            trending_label(i+1).configure(fg='#818182')
    except Exception:
        pass
    try:
        while True:
            Delete_color=poster_index#记录一个数，再经过一些处理得到上一个变红色的是多少,然后把它变回原来的颜色
            if Twice<9:
                Twice=Twice+1
            if poster_index==7:#如果已经循环一次了,那么就把要改变的数,变成第一个
                poster_index=0#如果已经循环一次了,那么就把要改变的数,变成第一个
            if Delete_color==0:#如果已经循环一次了,那么就把要改字体的数,变成循环的最后一个
                Delete_color=7#如果已经循环一次了,那么就把要改字体的数,变成循环的最后一个
            if state.carousel_stop!=Kill_i:#判断杀死机制,是否启动如果启动就把图片清空，然后把颜色调回，最后杀死本线程(关闭)
                state.carousel_label.configure(text="等待加载...              ",image=PhotoImage(file=''))#清空当前图片,并恢复文字
                trending_label(Delete_color).configure(fg="#818182")#颜色调回
                break#关闭
            if Twice<9:
                image_data=load_carousel_image(poster_index)#导入轮播图片
                w, h = image_data.size#获取当前宽高  
                image_data=Picture_transcoding(w, h, vgFrames["width"]//100*110, int(vgFrames["height"]//120*68), image_data)#将图片大小转化为可适应当前大小的尺寸
                image=ImageTk.PhotoImage(image_data)#转化为控件使用对象
                poster_cache[poster_index]=image#数据列入列表，以防每次都访问
                sleep(0.7)#等待0.7秒之后再开始切换
            else:#从网络获取图片需要时间,所以上面不需要等待太久下面需要,至于上面,虽然说比下面慢，但是时间还是挺快的，所以也需要一个等待
                sleep(1.1)#等待1.1秒之后再开始切换
            try:
                state.carousel_label.configure(image=poster_cache[poster_index], cursor="arrow")#由于有一个等待加载的原因,所以要把文字变空,并且抽出列表类数据显示
                state.carousel_label.configure(text="")
                trending_label(poster_index+1).configure(fg="#FF5C38")#将跟当前轮播图片对应的文字变成红色
                trending_label(Delete_color).configure(fg="#818182")#把跟当前轮播图片对应的上一个变回原来的颜色
            except Exception:
                pass
            poster_index=poster_index+1#给轮播数加一
    except Exception:
        pass




def load_elect_image(elect_label, url_index, page_index, frame_width, frame_height, rotation_height, img_name):#首页下方4个推荐位:后台拉图并缩放设置(原为四段 exec 线程)
    try:
        _page=state.recommend_pages[page_index]
        image_data=fetch_image(state.recommend_posters[url_index])#导入网络图片(fetch_image 内部已经 Image.open 过,这里不能再套一层,否则 AttributeError 被下面 except 吞掉→推荐位永远不显示)
        w, h = image_data.size#获取当前宽高
        image_data=Picture_transcoding(w, h, int(frame_width), int(frame_height-(rotation_height//135*8))//2, image_data)#将图片大小转化为可适应当前大小的尺寸
        image=ImageTk.PhotoImage(image_data)#转化为控件使用对象
        state.elect_images[img_name]=image#保留引用,防止被回收
        elect_label['image']=image#图片设置
        elect_label['cursor']="hand2"
        elect_label.bind("<Button-1>",lambda *Elect:Thread(target=lambda:_open_player(('video.exe 2 '+_page.rsplit(".html")[0][::-1].rsplit("/")[0][::-1]+' '+_download_dir_arg()))).start())
        elect_label.bind("<Button-1>",lambda eve:_hide_recommend(),"+")
    except Exception:
        pass
