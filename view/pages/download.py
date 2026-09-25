# -*- coding: utf-8 -*-
"""下载页(左侧导航第 7 项)

    download(vgFrame, style)   扫描"下载目录",按下载时间倒序列出已下好的视频,
                               可播放、可打开所在位置、可删除。

下载目录从 config.json 的 path.download_dir 读 —— 与标题栏菜单"文件下载位置"写的是同一份:
    目录里每部视频是 "<剧名>.mp4",封面是同名 "<剧名>.jpg",
    所以只把 .mp4 当成一条记录,封面跟着记录一起删。
下载中的临时目录(_dl_xxx)不进列表。
"""
import os
import subprocess
import sys
from threading import Thread
from time import strftime, localtime
from tkinter import Canvas, Frame, Label

import tkinter.ttk as ttk
import tkinter.messagebox

import model.state as state
from model.paths import IS_WINDOWS, _download_dir
from view.widgets import scrollbar
from controller.entry import VGvideo

_DL_VIDEO_EXT = ".mp4"      # 成品视频扩展名(见 model/download.py)
_DL_COVER_EXT = ".jpg"      # 同名封面
_DL_TMP_PREFIX = "_dl_"     # 下载中的临时目录前缀


def _dl_dir():  # 下载目录:统一从 config.json 的 path.download_dir 取(配置缺失时退回系统"下载"目录)
      try:
            return _download_dir()
      except Exception:
            return ""


def _dl_size(n):  # 字节数转成好读的大小
      try:
            n = float(n)
      except Exception:
            return "大小未知"
      for _u in ("B", "KB", "MB", "GB"):
            if n < 1024 or _u == "GB":
                  return ("%d %s" % (n, _u)) if _u == "B" else ("%.1f %s" % (n, _u))
            n /= 1024.0


def _reveal(path):  # 在文件管理器里定位到文件
      try:
            _p = os.path.normpath(path)
            if IS_WINDOWS:
                  subprocess.Popen('explorer /select,"%s"' % _p)
            elif sys.platform == "darwin":
                  subprocess.Popen(["open", "-R", _p])
            else:
                  subprocess.Popen(["xdg-open", os.path.dirname(_p)])
      except Exception as err:
            print("打开位置失败:", err)


def _open_dir(path):  # 打开整个下载目录
      try:
            if IS_WINDOWS:
                  os.startfile(os.path.normpath(path))
            elif sys.platform == "darwin":
                  subprocess.Popen(["open", path])
            else:
                  subprocess.Popen(["xdg-open", path])
      except Exception as err:
            print("打开目录失败:", err)


class download(object):
  def __init__(self, vgFrame, style):
    #不用在这里复位上一个导航项的高亮:Page_switching 切页时已经复位过了(见 main.py:231),
    #而这里拿到的 state.current_page 已经是本页,再复位就会把刚点亮的本项又抹掉。
    try:
          self.vgFrame = vgFrame
          self.style = style
          self.frame = Canvas(self.vgFrame, bg=style, highlightthickness=0)
          self.content = Frame(self.frame, bg=style)
          scrollbar.setup(self.vgFrame)#深色滚动条:必须带 map,只 configure 滑块中间会一直是白的
          x = Frame(self.frame, width=12, highlightthickness=0, bd=0, bg=style)
          x.pack(side="right", fill="y")
          self.scrollbar = ttk.Scrollbar(x, orient="vertical", command=self.frame.yview)
          self.frame.configure(yscrollcommand=self.scrollbar.set)
          self._cw = self.frame.create_window((0, 0), window=self.content, anchor='nw')
          self.scrollbar.place(x=0, y=-13, relheight=1, height=26, relwidth=1)
          self.frame.place(x=0, y=0, relheight=1, relwidth=1)
          self.frame.bind("<Configure>", lambda _e: self.frame.itemconfigure(self._cw, width=max(1, _e.width - 12 - _e.width // 80)))
          self.content.bind("<Configure>", lambda event: self.frame.configure(scrollregion=self.frame.bbox("all"), width=self.vgFrame["width"], height=self.vgFrame["height"]))
          self.content.bind("<MouseWheel>", self.Wheel)
          self.frame.bind("<MouseWheel>", self.Wheel)
          self.scrollbar.bind("<MouseWheel>", self.Wheel)
          self.refresh()
    except Exception as err:
      print("下载页初始化失败:", err)
  def Wheel(self, event):  # 鼠标滚轮:与历史页/搜索页一致
    try:
      if "win" in sys.platform:
        self.frame.yview_scroll(int(-1 * (event.delta / 120)), "units")
      else:
        self.frame.yview_scroll(int(-1 * event.delta), "units")
      return "break"
    except Exception:
      pass
  def bind_wheel(self, widget):  # 滚轮事件不会冒泡到父级,整行的子控件都要挨个绑
    try:
      widget.bind("<MouseWheel>", self.Wheel)
      for i in widget.winfo_children():
        self.bind_wheel(i)
    except Exception:
      pass
  def refresh(self):  # 重新扫描下载目录(首次进入与点"刷新"都走这里)
    try:
      _t = Thread(target=self.download_data)
      _t.daemon = True
      _t.start()
    except Exception as err:
      print("下载页刷新失败:", err)
  def _download_items(self):  # 返回 [[路径,文件名,大小,修改时间],...],新下的排最前
    _out = []
    _dir = _dl_dir()
    if not _dir or not os.path.isdir(_dir):
      return _out
    try:
      _names = os.listdir(_dir)
    except Exception:
      return _out
    for _name in _names:
      _low = _name.lower()
      if _low.startswith(_DL_TMP_PREFIX) or not _low.endswith(_DL_VIDEO_EXT):
        continue
      _p = os.path.join(_dir, _name)
      if not os.path.isfile(_p):
        continue
      try:
        _st = os.stat(_p)
      except Exception:
        continue
      _out.append([_p, os.path.splitext(_name)[0], _st.st_size, _st.st_mtime])
    _out.sort(key=lambda i: i[3], reverse=True)  # 最近下好的排最上面
    return _out
  def _mk_btn(self, parent, text, bg, hover, font, command):  # 统一样式的行内按钮(本项目用 Label 当按钮)
    _b = Label(parent, text=text, bg=bg, fg="#FFFFFF", font=font, cursor="hand2")
    _b.bind("<Enter>", lambda *e: _b.configure(bg=hover))
    _b.bind("<Leave>", lambda *e: _b.configure(bg=bg))
    _b.bind("<Button-1>", lambda *e: command())
    return _b
  def _remove(self, path, name):  # 删掉成品(连同同名封面),删完就地刷新
    if not tkinter.messagebox.askyesno("删除下载", "确定删除《%s》吗?\n(同名封面也会一起删掉)" % name):
      return
    try:
      os.remove(path)
      _cover = os.path.splitext(path)[0] + _DL_COVER_EXT
      if os.path.isfile(_cover):
        os.remove(_cover)
    except Exception as err:
      tkinter.messagebox.showwarning("删除失败", str(err))
    self.refresh()
  def download_data(self):  # 画列表:表头(数量/总大小/刷新/打开目录) + 每行(序号 文件名 大小·时间 播放/位置/删除)
    try:
      try:
        _w = int(float(self.vgFrame["width"]))
        _h = int(float(self.vgFrame["height"]))
      except Exception:  # 还没布局时退回实际尺寸
        _w, _h = self.vgFrame.winfo_width(), self.vgFrame.winfo_height()
      _dir = _dl_dir()
      _list = self._download_items()
      for _child in self.content.winfo_children():  # 刷新时先清掉上一版内容
        _child.destroy()
      _head = Frame(self.content, bg=self.style)
      _head.pack(fill="x")
      Label(_head, text="  已下载 %d 个视频 · 共 %s" % (len(_list), _dl_size(sum(_i[2] for _i in _list))),
            bg=state.style, fg="#FF5C38", font=("Comic Sans MS", -1 * _w // 52, "bold"), anchor='w').pack(side="left")
      self._mk_btn(_head, " 打开下载目录 ", "#3D3F44", "#4A4C52", ("Comic Sans MS", -1 * _w // 64),
                   lambda d=_dir: _open_dir(d) if d else None).pack(side="right", padx=(0, _w // 60))
      self._mk_btn(_head, " 刷新 ", "#3D3F44", "#4A4C52", ("Comic Sans MS", -1 * _w // 64),
                   self.refresh).pack(side="right", padx=(0, _w // 90))
      if not _list:
        Label(self.content, text=("还没有下载好的视频" if _dir else "还没有设置下载目录"), bg=state.style,
              fg="#DBDBDC", font=("Comic Sans MS", -1 * _w // 62)).pack(pady=_h // 4)
        Label(self.content, text=("下载目录:" + _dir) if _dir else "用右上角菜单 ≡ → 文件下载位置 选一个目录",
              bg=state.style, fg="#818182", font=("Comic Sans MS", -1 * _w // 82)).pack()
        Label(self.content, text="在播放器里点 ⇓ 就能把正在看的视频存到这里", bg=state.style,
              fg="#818182", font=("Comic Sans MS", -1 * _w // 82)).pack(pady=(_h // 80, 0))
        return
      _row_h = max(56, int(_h // 7))
      _font = ("Comic Sans MS", -1 * _w // 64)
      for _n, (_path, _nm, _size, _mtime) in enumerate(_list, 1):
        row = Frame(self.content, bg="#1C1E26", height=_row_h, highlightthickness=0)
        row.pack(fill="x", pady=max(1, _h // 100))
        row.pack_propagate(False)
        Label(row, text=f"{_n:02d}", bg="#1C1E26", fg="#4E4E54",
              font=("Comic Sans MS", -1 * _w // 62, "bold")).pack(side="left", padx=(_w // 70, _w // 90))
        box = Frame(row, bg="#1C1E26")
        box.pack(side="left", fill="both", expand=True)
        title = Label(box, text=" " + _nm, bg="#1C1E26", fg="#FFFFFF",
                      font=("Comic Sans MS", -1 * _w // 60, "bold"), cursor="hand2", anchor='w')
        title.pack(fill="x", pady=(_row_h // 8, 0))
        Label(box, text=" %s · %s" % (_dl_size(_size), strftime('%Y-%m-%d %H:%M', localtime(_mtime))),
              bg="#1C1E26", fg="#818182", font=("Comic Sans MS", -1 * _w // 82), anchor='w').pack(fill="x")
        self._mk_btn(row, " 播放 ", "#FF5C38", "#FF7300", _font,
                     lambda p=_path: Thread(target=lambda: VGvideo('video.exe 1 "%s"' % p), daemon=True).start()).pack(side="right", padx=(_w // 90, _w // 80))
        self._mk_btn(row, " 删除 ", "#3D3F44", "#4A4C52", _font,
                     lambda p=_path, t=_nm: self._remove(p, t)).pack(side="right", padx=(_w // 90, 0))
        self._mk_btn(row, " 打开位置 ", "#3D3F44", "#4A4C52", _font,
                     lambda p=_path: _reveal(p)).pack(side="right", padx=(_w // 90, 0))
        title.bind("<Enter>", lambda *e, w=title: w.configure(fg="#FF5C38"))
        title.bind("<Leave>", lambda *e, w=title: w.configure(fg="#FFFFFF"))
        title.bind("<Button-1>", lambda *e, p=_path: Thread(target=lambda: VGvideo('video.exe 1 "%s"' % p), daemon=True).start())
        self.bind_wheel(row)
    except Exception as err:
      print("下载记录加载失败:", err)
