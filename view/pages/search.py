# -*- coding: utf-8 -*-
"""搜索结果页(从 main.py 拆出)

    Searchs(vgFrames, style, 页码, 搜索词)   在给定容器里渲染搜索结果,底部带翻页

界面与接口分离:数据统一来自 model.api.search_qq(标准 JSON),本模块只负责画出来。
"""
import sys
from threading import Thread
from tkinter import Canvas, Frame, LabelFrame, Label, LEFT

import tkinter.ttk as ttk
import tkinter.messagebox
from PIL import ImageTk

import model.state as state
from model.paths import _download_dir_arg
from view.image import Picture_transcoding
from view.widgets import scrollbar
from model.api import search_qq, fetch_image, _resolve_url, play_fail_msg
from controller.entry import VGvideo


class Searchs(object):
    def __init__(self,vgFrames,style,The_number_of_pages,Searchs_text):
        if Searchs_text!="":
          self.Searchs_text=Searchs_text
          self.vgFrames=vgFrames
          self.frame=Canvas(self.vgFrames,bg=style,highlightthickness=0)
          self.content=Frame(self.frame,bg=style)
          scrollbar.setup(self.vgFrames)#深色滚动条:必须带 map,只 configure 滑块中间会一直是白的
          x=Frame(self.vgFrames,width=12,highlightthickness=0,bd=0,bg=style)
          x.pack(side="right",fill="y")
          self.scrollbar=ttk.Scrollbar(x,orient="vertical",command=self.frame.yview)
          self.frame.configure(yscrollcommand=self.scrollbar.set)
          self.frame.create_window((0,0),window=self.content,anchor='nw')
          self.scrollbar.place(x=0, y=-13, relheight=1,height=26,relwidth=1)
          self.frame.place(x=0, y=0,relheight=1,relwidth=1)
          #滚轮支持+滚动范围实时刷新:内容加载变高后随时更新 scrollregion,滚轮和滚动条才不会失灵
          self.frame.bind("<MouseWheel>",self.Wheel)
          self.scrollbar.bind("<MouseWheel>",self.Wheel)
          self.content.bind("<MouseWheel>",self.Wheel)
          self.content.bind("<Configure>",lambda event: self.frame.configure(scrollregion=self.frame.bbox("all"),width=vgFrames["width"],height=vgFrames["height"]))
          Search_data=Thread(target=self.Search_data,args=(self.content,The_number_of_pages))#多线程载入
          Search_data.daemon = True#守护线程
          Search_data.start()#启动
          self.frame.configure(scrollregion=self.frame.bbox("all"),width=vgFrames["width"],height=vgFrames["height"])
    def Search_data(self,frame,The_number_of_page):
        self.The_number_of_page=The_number_of_page
        distance=self.vgFrames["width"]//100
        width=int(self.vgFrames["width"]//1.05)
        large_height=int(self.vgFrames["height"]//4*1.5)
        Small_height=int(self.vgFrames["height"]//5)
        state.search_posters=[]#将图片储存在这里就可以避免同时使用一个变量出现的问题
        try:
          result=search_qq(self.Searchs_text,The_number_of_page)#得到标准 JSON:搜索词/页码/总页数/列表,展示与接口彻底分开
          items=result["items"]
          pages=max(1,int(result.get("pages") or 1))
        except Exception as err:#接口出错了也把界面兜住,只显示"下一页"失效而不至于整页崩溃
          print("搜索失败:",err)
          items=[]
          pages=The_number_of_page
        for item in items:
          try:
            kind=item.get("kind")#cover=剧集/影片(有cid,进详情);video=单条视频(有vid,解析后直接播)
            item_id=item.get("id") or ""
            item_title=item.get("title") or ""
            item_img=item.get("img") or ""
            item_desc=item.get("desc") or ""
            if not (item_id and item_img):
              continue
            if kind=="cover":
              image_data=fetch_image(item_img)#导入网络图片
              w,h=image_data.size
              image_data=Picture_transcoding(w,h,width//5,large_height,image_data)#将图片大小转化为可适应当前大小的尺寸
              state.search_posters.append(ImageTk.PhotoImage(image_data))#转化为控件使用对象,然后组成进入列表
              data=Frame(frame,width=width,height=large_height,highlightthickness=0)#内容
              datas=LabelFrame(data,bg=state.style,width=width,height=large_height,borderwidth=0)#内容里面放一个控制大小的东西
              img=Label(datas,bg=state.style,width=width//5,image=state.search_posters[len(state.search_posters)-1],height=large_height,bd=0,cursor="hand2")#图片
            else:
              image_data=fetch_image(item_img)#导入网络图片
              w,h=image_data.size
              image_data=Picture_transcoding(w,h,width//3,Small_height,image_data)#将图片大小转化为可适应当前大小的尺寸
              state.search_posters.append(ImageTk.PhotoImage(image_data))#转化为控件使用对象
              data=Frame(frame,width=width,height=Small_height,highlightthickness=0)
              datas=LabelFrame(data,bg=state.style,width=width,height=Small_height,borderwidth=0)
              img=Label(datas,bg=state.style,width=width//3,image=state.search_posters[len(state.search_posters)-1],height=Small_height,bd=0,cursor="hand2")
            img.place(x=0,y=0)
            def play(kind=kind,item_id=item_id):#统一入口:封面用 cid 进选集页;单视频用 vid 解析出地址再播放
                try:
                  if kind=="cover":
                    VGvideo(("video.exe 2 "+item_id+" "+_download_dir_arg()))#直接传入(下载目录统一从 config.json 取,带引号)
                  else:
                    address=_resolve_url(item_id)#解析出真实播放地址(调 config.json 里 PLAY_API_BASE 指定的解析服务,客户端本身不取流)
                    if not address:#解析不到(内容加密/会员权益/网络):别拿空地址开播放器,直接把原因告诉用户
                      _m=play_fail_msg() or "没有取到可播放的地址(会员 / 权益 / 登录态 / 网络)"
                      try: self.frame.after(0,lambda m=_m:tkinter.messagebox.showinfo("无法播放",m))#回到主线程弹窗,避免子线程操作 Tk
                      except Exception: print("播放失败:",_m)
                      return
                    VGvideo(("video.exe 3 "+address+" "+_download_dir_arg()))#得到地址传入(下载目录统一从 config.json 取,带引号)
                except Exception as err:
                  print("播放失败:",err)
            name=Label(datas,text=" "+item_title,font=("Comic Sans MS",-1*datas["width"]//28,"bold"),fg="#FF5C38",bg=state.style,cursor="hand2",anchor="ne")#视频名字
            name.place(x=img["width"],y=0)
            name.bind("<Button-1>",lambda *vgimg,play=play:Thread(target=play).start())#点名字播放
            img.bind("<Button-1>",lambda *vgimg,play=play:Thread(target=play).start())#点图片播放
            Label(datas,text="简介:"+item_desc,bg=state.style,font=("Comic Sans MS",-1*datas["width"]//45),wraplength=int((self.vgFrames["width"]-(img["width"]+datas["width"]//25))//1.1),fg="#FFFFFF",justify='left',anchor = 'w').place(x=img["width"]+datas["width"]//20,y=datas["width"]//18)#简介
            datas.pack()
            data.pack(pady=distance)
            self.bind_wheel(data)#给这条结果及其子控件绑上滚轮
          except:
            pass
        if not items:#搜索没有内容(关键词无结果/网络异常):画一张居中的空状态,免得界面一片黑像卡死了
          self._empty_state()
          if pages<=1:#只有一页又是空的,再摆个"下一页"只会让人以为还能点,不如不画
            self._loading=False#解锁:原来靠函数末尾那行解锁,这里提前 return 就得自己放行,否则翻页会永久卡住
            return
        The_number_of_pages=Frame(frame,bg=state.style)
        font_size=self.vgFrames["width"]//65*-1
        if The_number_of_page>1:#判断是否大于第1页，如果是就不禁用
          page_up_key=Label(The_number_of_pages, text="上一页",font=("Comic Sans MS",font_size),bg=state.style,fg="#DBDBDC",cursor="hand2")
          page_up_key.pack(side=LEFT, padx=5)
          page_up_key.bind("<Leave>",lambda *vgpage_up_key:page_up_key.configure(fg='#DBDBDC'))#离开时候变回
          page_up_key.bind("<Enter>",lambda *vgpage_up_key:page_up_key.configure(fg='#FF5C38'))#进入时变色
          page_up_key.bind("<Button-1>",lambda *next_page:self.switch(The_number_of_page-1))
        else:#判断是否是第1页，如果是就将上一页按钮禁用
          page_up_key=Label(The_number_of_pages, text="上一页",font=("Comic Sans MS",font_size),bg=state.style,fg="#4E4E54")
          page_up_key.pack(side=LEFT, padx=5)
          page_up_key.bind("<Leave>",lambda *Left_option_12vg:page_up_key.configure(fg='#4E4E54'))#离开时候变回
          page_up_key.bind("<Enter>",lambda *Left_option_12vg:page_up_key.configure(fg='#47474E'))#进入时变色
        if The_number_of_page!=int(pages):#判断是否大于第1页，如果是就不禁用
          next_page=Label(The_number_of_pages, text="下一页",font=("Comic Sans MS",font_size),bg=state.style,fg="#DBDBDC",cursor="hand2")
          next_page.bind("<Leave>",lambda *vgpage_up_key:next_page.configure(fg='#DBDBDC'))#离开时候变回
          next_page.bind("<Enter>",lambda *vgpage_up_key:next_page.configure(fg='#FF5C38'))#进入时变色
          next_page.bind("<Button-1>",lambda *next_page:self.switch(The_number_of_page+1))
        else:#判断是否是第1页，如果是就将上一页按钮禁用
          next_page=Label(The_number_of_pages, text="下一页",font=("Comic Sans MS",font_size),bg=state.style,fg="#4E4E54")
          next_page.bind("<Leave>",lambda *Left_option_12vg:next_page.configure(fg='#4E4E54'))#离开时候变回
          next_page.bind("<Enter>",lambda *Left_option_12vg:next_page.configure(fg='#47474E'))#进入时变色
        Label(The_number_of_pages, text=f"{The_number_of_page}",font=("Comic Sans MS",font_size),bg=state.style,fg="#DBDBDC").pack(side=LEFT)
        next_page.pack(side=LEFT, padx=5)
        The_number_of_pages.pack()
        self.bind_wheel(The_number_of_pages)#底部翻页条也支持滚轮滚动
        self._loading=False#本页加载完成,放行翻页
    def _empty_state(self):#搜索无结果的空状态:放大镜 + 主副标题,摆在视口正中
        # 直接挂在画布(self.frame)上而不是挂在 content 里:空状态没有内容撑高 content,
        # 挂在 content 里只能按内容高度定位(原来那行字被 pady 往下推,窗口一变高就跑出屏幕);
        # 挂画布上则永远相对整块视口居中,且不受滚动影响。
        try:
          _w=max(1,int(self.vgFrames["width"] or 1))
          _size=max(30,int(_w//22))#放大镜直径随窗口宽度缩放
          box=Frame(self.frame,bg=state.style)
          box.place(relx=0.5,rely=0.46,anchor="center")
          glass=Canvas(box,width=_size,height=_size,bg=state.style,highlightthickness=0,bd=0)
          glass.pack()
          _p=max(2,_size//8)#镜片四周留白
          _lw=max(2,_size//11)#描边粗细
          glass.create_oval(_p,_p,_size-_p*2,_size-_p*2,outline="#4E4E54",width=_lw)#镜片
          glass.create_line(_size-_p*2,_size-_p*2,_size-_p//2,_size-_p//2,fill="#4E4E54",width=_lw)#镜柄
          _wrap=max(160,int(_w//2.6))#文案换行宽度:窄窗口也不会被挤出屏幕
          _kw=str(self.Searchs_text or "").strip()
          Label(box,text=("没有找到“%s”的相关内容"%_kw) if _kw else "没有找到相关内容",
                bg=state.style,fg="#DBDBDC",font=("Comic Sans MS",-max(12,_w//48),"bold"),
                wraplength=_wrap,justify="center").pack(pady=(_size//4,4))
          Label(box,text="换个关键词试试;若是网络异常,稍后重试即可",
                bg=state.style,fg="#8A8A93",font=("Comic Sans MS",-max(10,_w//62)),
                wraplength=_wrap,justify="center").pack()
        except Exception as err:
          print("空状态绘制失败:",err)#画不出来也不能把搜索页拖崩
    def Wheel(self,event):#鼠标滚轮动作:滚轮在结果列表任意位置都能上下滚动
        try:
          if "win" in sys.platform:#windows系统需要除以120
            platform=int(-1*(event.delta/120))
          else:
            platform=int(-1*event.delta)
          self.frame.yview_scroll(platform, "units")
          return "break"
        except Exception:
          pass
    def bind_wheel(self,widget):#把控件连同所有子控件都绑上滚轮(滚轮事件不会自动冒泡到父级,必须挨个绑)
        try:
          widget.bind("<MouseWheel>",self.Wheel)
          for i in widget.winfo_children():
            self.bind_wheel(i)
        except Exception:
          pass
    def switch(self,cur):
        if getattr(self,"_loading",False):#上一页还没加载完就忽略这次点击,避免连点卡死/串页
          return
        self._loading=True#先锁住,防止加载期间重复点击翻页
        self.frame.destroy()#删除控件
        self.content.destroy()#删除控件
        self.scrollbar.destroy()#删除控件
        #将所有控件重新创造一次
        self.frame=Canvas(self.vgFrames,bg=state.style,highlightthickness=0)
        self.content=Frame(self.frame,bg=state.style)
        x=Frame(self.vgFrames,width=12,highlightthickness=0,bd=0,bg=state.style)
        x.pack(side="right",fill="y")
        self.scrollbar=ttk.Scrollbar(x,orient="vertical",command=self.frame.yview)
        self.frame.configure(yscrollcommand=self.scrollbar.set)
        self.frame.create_window((0,0),window=self.content,anchor='nw')
        self.scrollbar.place(x=0, y=-13, relheight=1,height=26,relwidth=1)
        self.frame.place(x=0, y=0,relheight=1,relwidth=1)
        self.frame.bind("<MouseWheel>",self.Wheel)
        self.scrollbar.bind("<MouseWheel>",self.Wheel)
        self.content.bind("<MouseWheel>",self.Wheel)
        self.content.bind("<Configure>",lambda event: self.frame.configure(scrollregion=self.frame.bbox("all"),width=self.vgFrames["width"],height=self.vgFrames["height"]))
        Search_data=Thread(target=self.Search_data,args=(self.content,cur))#多线程载入,避免翻页时界面卡死
        Search_data.daemon = True#守护线程
        Search_data.start()#启动
        self.frame.configure(scrollregion=self.frame.bbox("all"),width=self.vgFrames["width"],height=self.vgFrames["height"])
