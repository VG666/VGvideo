# -*- coding: utf-8 -*-
"""数据服务调用层(model.api.client)—— 客户端**唯一**的出网口

客户端自己不上网取数据:取流 / 选集 / 弹幕 / 标题 / 搜索 / 轮播 / 热词 / 直播 / 图片,
全部由这里发一次 HTTP GET,向**数据服务**要(源码、协议、接口清单见数据源项目说明)。
v.qq.com、咪咕、图片 CDN 这些第三方站点一律由服务端去取 ——
于是"这条数据到底从哪来"永远只有一个答案:

    数据源 = config/config.json 里 vgapi.PLAY_API_BASE 指向的那台 VG 数据服务

要核对数据源,看两处即可:
    1) config/config.json 的 vgapi.PLAY_API_BASE —— 数据服务地址,也就是数据源本体;
    2) 控制台里带 [数据源] 前缀的行 —— 每次请求打的是哪个接口、发去哪个地址,都写在上面。

对外就三个函数,其它模块一律不许自己 urlopen / Request:
    request_json(path, params, default)   解析好的 JSON(服务端 {"code":0,"data":…} 自动拆出 data)
    request_text(path, params, default)   原始文本(如 /episodes,服务端原样透传数据源的 JSON 文本)
    request_bytes(path, params)           原始字节(如 /image 图片代理)

约定:
    * 失败一律返回空值(None / "" / (b"", ""))、不抛异常 —— 界面不会因为服务连不上而崩;
    * 口令走 X-Api-Token 请求头(也兼容地址里的 ?token=),对应服务端的 API_TOKEN;
    * 每个请求最多发两次(网络抖动重试一次),超时取 PLAY_API_TIMEOUT。
"""
from json import loads
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from . import config

_UA = "VGVideo/1.0"     # 客户端自己的 UA;对数据源用什么 UA 由服务端决定,与这里无关
QUIET = False           # True = 连 [数据源] 日志也不打(批量自测时可临时打开)


def _log(msg):
    if not QUIET:
        print("[数据源] %s" % msg)


def base():
    """数据服务地址(末尾不带 /);没配置返回空串 —— 空串就等于"没有数据源" """
    return str(getattr(config, "PLAY_API_BASE", "") or "").strip().rstrip("/")


def token():
    """服务端口令(服务端 API_TOKEN 留空时,这里也留空)"""
    return str(getattr(config, "PLAY_API_TOKEN", "") or "").strip()


def timeout(default=20.0):
    """单次请求超时(秒)"""
    try:
        return float(getattr(config, "PLAY_API_TIMEOUT", default) or default)
    except Exception:
        return float(default)


def source_line():
    """一行"数据来源"说明:界面提示 / 自测日志用,一眼看出数据取自哪里"""
    _b = base()
    return ("数据服务 " + _b) if _b else "未配置数据服务地址(config/config.json 的 vgapi.PLAY_API_BASE)"


def _url(path, params=None):
    """拼出完整请求地址;没配数据服务地址返回空串"""
    _b = base()
    if not _b:
        return ""
    _q = urlencode({str(k): v for k, v in (params or {}).items() if v not in ("", None)})
    if token():
        _q = (_q + "&" if _q else "") + "token=" + quote(token(), safe="")
    return ("%s%s?%s" % (_b, path, _q)) if _q else ("%s%s" % (_b, path))


def _open(url, t):
    _h = {"User-Agent": _UA, "Accept": "application/json"}
    if token():
        _h["X-Api-Token"] = token()
    return urlopen(Request(url, headers=_h), timeout=t)


def request_text(path, params=None, t=None, default="", quiet=False):
    """要一段文本;失败返回 default。quiet=True 时连"取不到"也不打日志(探活用)"""
    _u = _url(path, params)
    if not _u:
        if not quiet:
            _log("未配置数据服务地址(vgapi.PLAY_API_BASE),跳过 %s" % path)
        return default
    if not quiet:
        _log("GET %s" % _u)
    _to = float(t or timeout())
    for _i in (0, 1):                    # 网络抖一下很常见,重试一次就够
        try:
            return _open(_u, _to).read().decode("utf-8", "replace")
        except Exception as _e:
            if _i and not quiet:
                _log("%s 取不到(%s)" % (path, _e))
    return default


def request_json(path, params=None, t=None, default=None, quiet=False):
    """要一份 JSON;失败返回 default。

    服务端统一响应 {"code":0,"data":…} 时自动拆出 data;code≠0 表示这次数据源没拿到东西
    (结果是空的),按失败处理。其余接口(/play /health /rotation /episodes)没有 data 键,原样返回。
    """
    _txt = request_text(path, params, t=t, default="", quiet=quiet)
    if not _txt:
        return default
    try:
        _obj = loads(_txt)
    except Exception as _e:
        _log("%s 返回的不是 JSON(%s)" % (path, _e))
        return default
    if isinstance(_obj, dict) and "code" in _obj and "data" in _obj:
        try:
            if int(_obj.get("code") or 0) != 0:
                return default
        except Exception:
            return default
        return _obj["data"]
    return _obj


def request_bytes(path, params=None, t=None):
    """要原始字节(图片代理 /image 用):返回 (字节, Content-Type);失败返回 (b"", "")"""
    _u = _url(path, params)
    if not _u:
        _log("未配置数据服务地址(vgapi.PLAY_API_BASE),跳过 %s" % path)
        return b"", ""
    _log("GET %s" % (_u if len(_u) <= 200 else _u[:200] + "…"))
    try:
        _r = _open(_u, float(t or timeout()))
        return _r.read(), (str(_r.headers.get("Content-Type") or "").strip() or "image/jpeg")
    except Exception as _e:
        _log("%s 取不到(%s)" % (path, _e))
        return b"", ""
