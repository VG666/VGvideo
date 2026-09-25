# -*- coding: utf-8 -*-
"""直播频道数据(model.api.live_src)—— 频道表由数据服务给出

    GET {PLAY_API_BASE}/live
        → {"code":0,"data":{分类名:[[地址, 名称, 备注, 封面], …], …}}

"从哪拿频道"这件事全在服务端(数据源项目的 sources/live.py):
留空 config 的 LIVE_M3U 就用内置公开直链清单,填了 m3u/m3u8 地址或本地文件就用那一份。
客户端只把这份表拿回来渲染,不再自己读播放列表。
"""
from . import client


def live_channel_data():
    """直播频道表 {分类: [[地址, 名称, 备注, 封面], …]};取不到返回 {}"""
    _j = client.request_json("/live", default=None)
    return _j if isinstance(_j, dict) else {}


def live_channel_url(key):
    """频道项 → 可播地址。

    地址已由服务端整理好(m3u 里的原样、内置清单里的直链),这里不再做任何改写;
    入参本来就是空 / None 时返回空串。
    """
    return str(key or "").strip()
