# -*- coding: utf-8 -*-
"""发现页数据(model.api.discover)—— 全部向数据服务要

轮播海报 / 搜索热词 / 联想词 / 图片,客户端一样不自己出网:
    GET /rotation?frequency=   首页"重磅推荐"轮播 → (海报,标题,详情页链接,缩略图) 四元组
    GET /hot_words             搜索热词
    GET /suggest?kw=&field=    搜索联想词
    GET /image?url=            图片代理:服务端把图片取回来,客户端再用 PIL 打开显示

真正的抓取与解析在服务端(数据源项目的 sources/discover.py)。
本文件只保留"发请求 + 把结果摆成界面要的形状",失败一律给空值,界面自己会回落占位图。
"""
from io import BytesIO

from . import client

_HOT_TTL = 1800                 # 热词很少变,客户端也缓存半小时,免得搜索框一聚焦就打服务端
_HOT = {"t": 0.0, "v": []}


def _fetch_rotation_data(frequency):
    """首页轮播数据:返回 (海报, 标题, 详情页链接, 缩略图) 四元组,长度至少 8;取不到就是长度 8 的空串列表"""
    _j = client.request_json("/rotation", {"frequency": frequency}, default=None)
    if not isinstance(_j, dict):
        _j = {}
    _pics = list(_j.get("pics") or [])
    _names = list(_j.get("names") or [])
    _covers = list(_j.get("covers") or [])
    _thumbs = list(_j.get("thumbs") or [])
    _need = max(8, len(_pics))

    def _pad(_a):
        _base = _a or [""]
        while len(_a) < _need:
            _a.append(_base[len(_a) % len(_base)])
        return _a

    return _pad(_pics), _pad(_names), _pad(_covers), _pad(_thumbs)


def search_hot_words():
    """搜索热词;取不到返回 []。结果在客户端侧也缓存 _HOT_TTL 秒"""
    from time import time
    if _HOT["v"] and time() - _HOT["t"] < _HOT_TTL:
        return list(_HOT["v"])
    _v = [str(x) for x in (client.request_json("/hot_words", default=[]) or []) if str(x).strip()]
    if _v:
        _HOT["t"], _HOT["v"] = time(), _v
    return list(_v or _HOT["v"])


def search_suggest(keyword, field="word"):
    """搜索联想词;field=word 按词、field=tt 按片名;取不到返回 []"""
    _kw = str(keyword or "").strip()
    if not _kw:
        return []
    _v = client.request_json("/suggest", {"kw": _kw, "field": field or "word"}, default=[]) or []
    return [str(x) for x in _v if str(x).strip()]


def fetch_image(url):
    """取一张图片(PIL.Image);url 为 null / 空 / 取不到时返回 None。

    图片本体不在这里出网:交给数据服务的 /image 代理取回(客户端 PIL 只管打开显示)。
    """
    _u = str(url or "").strip()
    if not _u:
        return None
    try:
        from PIL import Image
    except Exception as _e:                       # 打包环境缺 Pillow 时不该把界面整崩
        print("[数据源] 缺少 Pillow,图片无法显示:", _e)
        return None
    if "://" not in _u:                           # 本地文件(海报缓存 / 调试图片)直接打开
        try:
            return Image.open(_u)
        except Exception as _e:
            print("[数据源] 本地图片打开失败(%s):%s" % (_u, _e))
            return None
    _data, _ = client.request_bytes("/image", {"url": _u})
    if not _data:
        return None
    try:
        return Image.open(BytesIO(_data))         # 注意:BytesIO 要一直活着,返回的 Image 才读得到像素
    except Exception as _e:
        print("[数据源] 图片解析失败:%s" % _e)
        return None
