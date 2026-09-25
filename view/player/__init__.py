# -*- coding: utf-8 -*-
"""播放器窗口:按职责分成 6 个 mixin,由 app.py 组装成 App。

    from view.player.app import App                  # 组装好的播放器窗口
    from view.player.playback import PlaybackMixin   # 只取某一个职责

本文件不转发子模块,避免循环依赖。
"""
