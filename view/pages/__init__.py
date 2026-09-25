# -*- coding: utf-8 -*-
"""各个内容页面(从 main.py 拆出):搜索 / 历史记录 / 下载 / 直播间 / 首页。

每个页面一个文件、一个类,各自 import 自己用到的依赖;
本文件不转发子模块,避免循环依赖(请写 from view.pages.search import Searchs)。
"""
