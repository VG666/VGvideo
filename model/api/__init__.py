# -*- coding: utf-8 -*-
"""API 汇总模块 —— 客户端这一层**只用来获取**,不生产数据

数据从哪来?一句话:全部来自**数据服务**(数据源项目)。
本包不做任何第三方抓取,连数据源的域名都不直接连;每个函数都是"发一次 HTTP 去数据服务要结果"。
数据源地址 = config/config.json 的 vgapi.PLAY_API_BASE;接口清单与部署见数据源项目说明。

模块分工(拍平在一个包里,主程序只从这一层 import):
    config.py     配置:客户端只读 PLAY_API_* 四项;其余(QQ_* / API_BASE / PLAY_BACKENDS / LIVE_M3U)
                  是给服务端继承的"数据源参数"(数据源项目的 config 会读同一份 config.json)
    client.py     唯一的出网口:三个 request_* 函数,失败返回空值不抛异常
    util.py       纯文本小工具(JSON 解析、地址日志),不含网络请求
    remote.py     取流调用层:vid → 真实播放地址(GET /play),带缓存与失败原因
    qq.py         选集 / 弹幕 / 标题 / 会员探测(GET /episodes /danmu /title /vip_probe)
    discover.py   轮播海报 / 热词 / 联想词 / 图片代理(GET /rotation /hot_words /suggest /image)
    search.py     搜索结果(GET /search);live_src.py 直播频道表(GET /live)

取流(播放地址解析)统一走 model.api.remote —— 客户端只有这一条路,不再有"本机解析"分支:
本地模式已彻底移除(localplay/ 已删除),不再有进程内取流、不再自动拉起本机服务。

用法:
    from model.api import *                        # 主程序:一句拿到全部接口
    _u = _resolve_url("r0047gdjpw6")               # 取流:向数据服务要地址
    ok, msg = play_api_health()                    # 看数据服务在不在线
    print(source_line())                           # 看一眼当前数据源地址

    import model.api
    r = model.api.search_qq("斗罗大陆", 1)           # 搜索:同样是数据服务给的

新增接口时:
    先把抓取逻辑放到数据源项目(并在其入口挂一个路由),
    再到本包对应模块写一个转调函数,最后到下面两处各补一行 —— 一是 import 那批名字,二是 __all__。
"""
from . import client, config, discover, live_src, qq, remote, search, util

# 数据源入口(client):三个 request_* + 数据源地址,api 层只从这里出网
from .client import request_bytes, request_json, request_text, source_line

# 配置(config):默认值 + 读写 config/config.json
from .config import (API_BASE, LIVE_M3U, PLAY_API_BASE, PLAY_API_CACHE, PLAY_API_TIMEOUT,
                     PLAY_API_TOKEN, PLAY_BACKENDS, QQ_COOKIE, QQ_COOKIE_CACHE, QQ_GUID,
                     QQ_STREAM_HTTP, QQ_UA_MB, QQ_UA_PC, QQ_USE_VINFO, QQ_VAPPID,
                     QQ_VINFO_REFERER, QQ_VSECRET, cfg_path, config_path, configure,
                     download_dir, get, main_argv, run_dir)

# 通用小工具(util):纯文本处理,不联网
from .util import _json_load, _log_play_url

# 取流调用层(remote):play_api_* 是这批网络接口的对外叫法,与 remote 里的原名一一对应
from .remote import api_base, health, last_fail, resolve, resolve_url
play_api_base = api_base                    # 数据服务地址(GET {base}/play)
play_api_health = health                    # 探活(GET {base}/health)
play_api_last_fail = last_fail              # 上次失败原因

# 数据源:取流入口 + 选集 / 弹幕 / 标题(全部转调数据服务)
from .qq import (_qq_cover_id, _qq_danmu, _qq_ep_no, _qq_ep_title, _qq_episodes,
                 _qq_is_web_page, _qq_play_title, _qq_url_to_vid, _qq_video_title,
                 _qq_vip_probe, _resolve_url, _resolve_url_info, play_fail_msg)

# 轮播 / 热词 / 图片;搜索数据源(search 改名成 search_qq,避免与下面的模块名撞车)
from .discover import _fetch_rotation_data, fetch_image, search_hot_words, search_suggest
from .search import SOURCE, search as search_qq

# 直播频道表
from .live_src import live_channel_data, live_channel_url

__all__ = [
    # 子模块(便于 model.api.xxx 直取)
    "config", "client", "util", "remote", "qq", "discover", "search", "live_src",
    # 数据源入口
    "request_text", "request_json", "request_bytes", "source_line",
    # 配置
    "run_dir", "main_argv", "configure", "get", "cfg_path", "config_path", "download_dir",
    "API_BASE", "QQ_COOKIE", "QQ_UA_PC", "QQ_UA_MB", "QQ_GUID", "QQ_USE_VINFO",
    "QQ_VINFO_REFERER", "QQ_VAPPID", "QQ_VSECRET", "QQ_STREAM_HTTP", "QQ_COOKIE_CACHE",
    "PLAY_BACKENDS", "PLAY_API_BASE", "PLAY_API_TOKEN",
    "PLAY_API_TIMEOUT", "PLAY_API_CACHE", "LIVE_M3U",
    # 通用小工具
    "_json_load", "_log_play_url",
    # 取流(向数据服务要地址)
    "api_base", "health", "last_fail", "resolve", "resolve_url",
    "play_api_base", "play_api_health", "play_api_last_fail",
    # 直播
    "live_channel_data", "live_channel_url",
    # 数据源
    "_qq_is_web_page", "_qq_url_to_vid", "_resolve_url_info", "_resolve_url",
    "_qq_cover_id", "_qq_ep_no", "_qq_episodes", "_qq_ep_title", "_qq_danmu",
    "_qq_video_title", "_qq_play_title", "_qq_vip_probe", "play_fail_msg",
    # 轮播 / 热词 / 图片 / 搜索
    "_fetch_rotation_data", "search_hot_words", "search_suggest", "fetch_image",
    "SOURCE", "search_qq",
]
