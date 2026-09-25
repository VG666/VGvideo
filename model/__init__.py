# -*- coding: utf-8 -*-
"""Model 层 —— 数据与业务逻辑(不画界面)。

    state.py     跨模块共享状态(唯一一处可变全局)
    paths.py     程序目录 / 数据文件路径 / 平台标记
    records.py   观看记录 Recordset/*.json 读写
    engine.py    VLC 播放引擎封装
    download.py  aria2 + ffmpeg 下载
    api/         全部网络接口(取流解析、直播、通用请求)

约定:本层不 import view / controller。
"""
