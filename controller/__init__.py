# -*- coding: utf-8 -*-
"""Controller 层 —— 流程控制。

    entry.py     命令行参数解析 / 启动主界面或播放器窗口

约定:叶子模块(页面、控件)也会直接调用本层的 VGvideo() 来开播放窗口,
      这条 view -> controller 的依赖是原有设计,保留不动。
"""
