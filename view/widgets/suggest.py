# -*- coding: utf-8 -*-
"""搜索框热词下拉(从 VG_video 里拆出)。

    focus_in(main)    输入框获得焦点:拉出"热门推荐"下拉框
    focus_out(main, e)  失去焦点:恢复提示文字/颜色,选中的词直接去搜

下拉框本身是个 overrideredirect 的 Toplevel,跟着输入框移动;
主窗口里保留 FocusIn / FocusOut 两个同名方法做转发(因为要能当回调绑)。
"""
import tkinter as tk
from tkinter import Entry, Label, Listbox, END

from model.api import search_hot_words
from view.layout import input_place_kw, INPUT_RELWIDTH_NORMAL, INPUT_RELWIDTH_MAXIMIZED


def focus_in(s, *event):#获取焦点
    if event!=():
      if s.Search_input["fg"]=="#BABABA":#判断是不是推荐的颜色
        s.Search_input.delete(0, END)#不是的话清空所有东西
      s.Search_input["fg"]="#FFFFFF"#这你不用管，因为获取之后怎么着都是这个颜色
      s.Search_input.bind("<Button-3>",lambda *Search_input_button_2vg: s.Search_input_button_2.post(Search_input_button_2vg[0].x_root,Search_input_button_2vg[0].y_root))
      s.recommend.configure(bg="#25252A")
      s.recommend.overrideredirect(True)
      s.recommend.attributes('-topmost',1)
      s.recommend.geometry(f"{s.Search_input_master.winfo_width()-s.Search_input_master.winfo_height()//2*2}x200+{s.Search_input_master.winfo_x()+s.window.winfo_x()+s.Search_input_master.winfo_height()//2}+{s.Search_input_master.winfo_y()+s.Search_input_master.winfo_height()+s.window.winfo_y()+3}")
      try:
        s.recommendLabel.destroy()
      except:
        pass
      try:
        s.recommendList.destroy()
      except:
        pass
      s.recommendLabel=Label(s.recommend,text="热门推荐",bg="#25252A",highlightbackground="#25252A",fg="#FFFFFF",font=("TkDefaultFont",(s.Search_input_master.winfo_x()+s.window.winfo_width())//90,"bold"),anchor='nw')
      s.recommendLabel.pack(fill="x")
      s.recommendList=Listbox(s.recommend,borderwidth=0,highlightthickness=0,bg="#25252A",highlightbackground="#25252A",fg="#BBBBBB",font=("TkDefaultFont",(s.Search_input_master.winfo_x()+s.window.winfo_width())//100),cursor="hand2")
      s.recommendList.pack(fill="both",expand=tk.YES)
      s.recommendList.bind("<<ListboxSelect>>",lambda event:[s.FocusOut(s.recommendList.get(i)) for i in s.recommendList.curselection()])
      s.recommendList.bind("<<ListboxSelect>>",lambda event:s.recommend.withdraw(),"+")
      if s.Search_input.get()=="":#只有输入框为空才推荐热词
        for i in search_hot_words():#搜索推荐词,数据源统一在 search_hot_words()
          s.recommendList.insert(END,"  "+i)
        s.recommend.deiconify()
      else:#有输入内容:提示框直接消失,不再请求联想词接口(接口不可靠会卡住界面)
        s.recommendLabel.pack_forget()
        s.recommendList.delete(0, END)
        s.recommend.withdraw()
      s.recommend.after(1,s.FocusIn)         
    else:
      if s.Search_input.get()!=s.input_get[-1][-1]:
        s.recommendList.delete(0, END)
        if s.Search_input.get()=="":#只有输入框为空才推荐热词
          s.recommendLabel.pack_forget()
          s.recommendList.pack_forget()
          s.recommendLabel.pack(fill="x")
          s.recommendList.pack(fill="both",expand=tk.YES)
          for i in search_hot_words():#搜索推荐词,数据源统一在 search_hot_words()
            s.recommendList.insert(END,"  "+i)
          s.recommend.deiconify()
          s.input_get.append([s.Search_input.get()])
        else:#有输入内容:提示框直接消失
          s.recommendLabel.pack_forget()
          s.recommendList.pack_forget()
          s.recommend.withdraw()
          s.input_get.append([s.Search_input.get()])
      s.recommend.geometry(f"{s.Search_input_master.winfo_width()-s.Search_input_master.winfo_height()//2*2}x200+{s.Search_input_master.winfo_x()+s.window.winfo_x()+s.Search_input_master.winfo_height()//2}+{s.Search_input_master.winfo_y()+s.Search_input_master.winfo_height()+s.window.winfo_y()+3}")
      s.recommend.after(1,s.FocusIn)

def focus_out(s, event):#失去焦点
  if type(event)==type(""):
    s.Search_input.delete(0, END) 
    s.Search_input.insert(END,event[2:])
    s.Search()
  Search=s.Search_input_master#得到数据，这个是好处理
  if s.Search_input.get()=="":#判断是否是空
      text,fg=s.Search_input_text,"#BABABA"#如果是就改成推荐的文字以及推荐的颜色
  else:
      text,fg=s.Search_input.get(),"#FFFFFF"#如果不是，就变回原来的文字以及输入时的颜色
  s.Search_input.destroy()#删除
  s.Search_input=Entry(Search,bg="#393942",bd=0,font=("微软雅黑",(-1*(int(Search["height"]))//10*4)),fg=fg,exportselection=0,highlightbackground="#FFFFFF")#输入框重新创建,且将指定的颜色填入
  if s.Maximize_ty:
    s.Search_input.place(**input_place_kw(Search,INPUT_RELWIDTH_NORMAL))#定位重新定位(算式统一在 view/layout.py)
  else:
    s.Search_input.place(**input_place_kw(Search,INPUT_RELWIDTH_MAXIMIZED))#定位重新定位
  s.Search_input.insert(tk.END,text)#将指定的文字填入
  s.Search_input.bind("<Return>",lambda *Search_confirmations:s.Search())#回车
  s.Search_input.bind('<FocusIn>',s.FocusIn)#重新绑定获取焦点
  s.Search_input.bind('<FocusOut>',s.FocusOut)#重新绑定失去焦点
  s.window.after(150,lambda:s.recommend.withdraw())
