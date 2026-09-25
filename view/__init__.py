# -*- coding: utf-8 -*-
"""View 层 —— 界面(画控件 + 绑回调)。

    chrome.py    无边框窗口公共逻辑 + 输入框剪贴板助手
    image.py     图片缩放 / 窗口图标 / 控件属性安全设置
    widgets/     通用控件:搜索框 / 标题栏 / 左侧导航 / 轮播 / 选集 / 联想
    pages/       页面:主窗口 / 首页 / 搜索结果 / 观看记录 / 咪咕直播
    player/      播放器窗口(6 个职责 mixin + app.py 组装成 App)

约定:界面代码里仍混着事件处理(原 main.py 就是 View+Controller 合体),
      拆成纯 MVC 需要重写事件逻辑,这里只按职责归层,不改变行为。
"""
