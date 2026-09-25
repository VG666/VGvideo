# -*- coding: utf-8 -*-
"""搜索数据源(model.api.search)—— 客户端只"发起搜索",结果由数据服务给出

    GET {PLAY_API_BASE}/search?q=<关键词>&page=1
        → {"source":"vg-server","keyword":"…","page":1,"pages":14,"total":400,
           "items":[{"kind":"cover|video","id":"…","title":"…","img":"…","desc":"…"}, …]}

抓取 / 解析 / 去重 / 分页统计这些活全在服务端(数据源项目的 sources/search.py),
本文件只负责把词和页码递过去、把空结果摆成界面能吃的形状。
与旧版接口完全同构(同样返回 items / pages / total),所以页面代码不用改。
"""
from . import client

# 数据源标识:搜索结果里带回来给界面/日志确认"这批数据是从哪拿的"(真正的实现在服务端)
SOURCE = {"name": "vg-server", "page_size": 20}


def search(keyword, page=1):
    """搜索一页:返回 {"source","keyword","page","pages","total","items"};失败返回同构的空结果"""
    _kw = str(keyword or "").strip()
    _pg = max(1, int(page or 1))
    _empty = {"source": SOURCE["name"], "keyword": _kw, "page": _pg, "pages": 0, "total": 0, "items": []}
    if not _kw:
        return _empty
    _j = client.request_json("/search", {"q": _kw, "page": _pg}, default=None)
    if not isinstance(_j, dict):
        return _empty
    for _k, _d in (("source", SOURCE["name"]), ("keyword", _kw), ("page", _pg),
                   ("pages", 0), ("total", 0), ("items", [])):
        _j.setdefault(_k, _d)
    return _j
