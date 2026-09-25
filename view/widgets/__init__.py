# -*- coding: utf-8 -*-
"""通用小件(从 main.py 拆出):导航助手 / 轮播与推荐位 / 选集。

只放"多个页面都要用"的零散能力,不放窗口和页面本身。
各子模块请各自 import(如 from view.widgets.carousel import carousel_loop),
本文件不转发子模块,避免循环依赖。
"""
