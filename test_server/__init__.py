# -*- coding: utf-8 -*-
"""测试数据源(服务端)

一个**完全不出网**的数据服务:接口、响应结构与 tx_server/ 一模一样,
但里面的数据全是本地现造的(目录见 catalog.py,占位封面见 cover.py,
能真播的音轨见 tone.py)。

它存在的意义:证明这个客户端是个"壳子" ——
把数据源地址(config/config.json 的 vgapi.PLAY_API_BASE)指到本服务,
首页轮播 / 搜索 / 选集 / 播放 / 弹幕 / 直播就全都能跑,而客户端一行代码都不用改。

单独跑:      python test_server/app.py            # 默认 127.0.0.1:8790
作为库调用:  from test_server.app import start_background   # 自动化测试里本机起一份用
接口清单:    GET /   (用浏览器打开就能看到)
"""
