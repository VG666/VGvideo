# -*- coding: utf-8 -*-
"""深色滚动条样式 —— 全项目唯一入口

    scrollbar.setup(widget)   把 ttk 主题切到 clam,并把竖/横滚动条染成深色

为什么必须集中在一处(而不是各页面各自 theme_use + configure):

1) clam 主题下,滚动条滑块的**填充色不取** configure 里的 -background。
   只写 styles.configure("Vertical.TScrollbar", background=深色, ...) 的话,
   轨道(troughcolor)、滑块描边(lightcolor/darkcolor)都会变深,
   唯独滑块正中间那一条仍然是主题默认的 #dcdad5 —— 深色界面上看就是一条白条。
   实测:配置完整个滑块只有 1px 描边是深色,中间 11px 全是 #dcdad5。

2) 原因是 ttk 的选项解析路径:只有当该选项存在**状态映射(map)**时,
   Tcl 才会去查映射表、并在没有状态匹配时回落到 configure 的值;
   完全没建 map 时,这个填充回落到了主题默认色。所以 configure 与 map 必须成对出现,
   少一个就是白条。

3) 另外 theme_use() 会重载该主题的默认样式,把之前 configure 的滚动条颜色冲掉。
   散落在各页面里各配一份,很容易被后一个页面冲回默认 —— 观感上的"白"就是这么来的。

所以这里统一:主题不是 clam 才切一次(已经是就不重复切,免得自己把刚配的颜色冲掉),
切完立刻按深色重配 configure + map。任何页面在创建滚动条之前调一下 setup() 即可。
"""
import tkinter.ttk as ttk

THEME = "clam"         # 必须 clam:vista 主题下滚动条颜色根本配不动
THUMB = "#3D3F44"      # 滑块常态
THUMB_ON = "#4A4C55"   # 滑块悬停:只提亮一档,给点反馈又不会突然发白
THUMB_DOWN = "#55575F" # 滑块按下
TROUGH = "#26262B"     # 轨道/槽

# 三个名字都配:不带前缀的基样式名会让所有未单独命名的滚动条跟着走,避免漏网
NAMES = ("Vertical.TScrollbar", "Horizontal.TScrollbar", "TScrollbar")


def setup(widget=None, thumb=THUMB, trough=TROUGH):
    """把滚动条染成深色。

    widget: 任意控件即可(只用它所属的 Tk 解释器来设样式),传 None 走默认 root。
    thumb/trough: 需要跟某块界面完全同色时可以单独传。
    返回 ttk.Style 实例,失败返回 None(样式配不上也不该把界面搞崩)。
    """
    try:
        s = ttk.Style(widget)
        if s.theme_use() != THEME:#已经是 clam 就别再切:theme_use 会重载主题,把自己刚配的颜色冲掉
            s.theme_use(THEME)
        for _n in NAMES:
            s.configure(_n, gripcount=0,
                        background=thumb, darkcolor=thumb, lightcolor=thumb,
                        troughcolor=trough, arrowcolor=trough, bordercolor=trough)
            # map 不是可选项:没有它,滑块的填充会回落主题默认的浅色 #dcdad5(白条就是这么来的)。
            # 顺便把悬停/按下的颜色也一起定死,不写的话鼠标一压上来就会回落到 clam 默认的浅色。
            s.map(_n,
                  background=[("pressed", THUMB_DOWN), ("active", THUMB_ON)],
                  darkcolor=[("pressed", THUMB_DOWN), ("active", THUMB_ON)],
                  lightcolor=[("pressed", THUMB_DOWN), ("active", THUMB_ON)],
                  troughcolor=[("pressed", trough), ("active", trough)],
                  arrowcolor=[("pressed", trough), ("active", trough)],
                  bordercolor=[("pressed", trough), ("active", trough)])
        return s
    except Exception as err:
        print("滚动条样式设置失败:", err)
        return None
