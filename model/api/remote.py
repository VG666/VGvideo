# -*- coding: utf-8 -*-
"""取流调用层(model.api.remote)—— vid → 真实播放地址

客户端**没有**取流实现,也不再在本机起服务:地址一律向数据服务(数据源项目)要。
本模块只做三件事 —— 发那一次 HTTP、把结果缓存起来、把"为什么没取到"整理成人能看懂的一句话。

接口(服务端实现见数据源项目,协议见数据源项目说明):
    GET {PLAY_API_BASE}/play?vid=<vid>&cid=<可选>
        → {"code":0,"url":"http://….m3u8?…","source":"vinfo","cached":0}
        → {"code":1,"url":"","source":"","reason":"drm|none","msg":"…"}
          reason=drm:流取到了,但全是 Widevine/PlayReady 加密的(本机播放器解不了),不是网络问题
    GET {PLAY_API_BASE}/health
        → {"code":0,"ok":true,"version":"1.1","backends":["vinfo","getinfo","aggregate"]}

对外入口(界面层只用这几个):
    resolve(vid, cid)      完整结果 {"url","source","reason","msg"};url 为空即失败
    resolve_url(vid, cid)  只要地址,失败返回空串(老写法,行为与以前一致)
    last_fail()            最近一次失败的 (原因码, 说明),供界面提示"为什么放不了"
    health()               探活 → (是否在线, 说明文本)
    api_base()             当前数据服务地址(= 数据源)

缓存:同一 vid(+cid)在 PLAY_API_CACHE 秒内不再打服务端,播放页重进 / 选集来回切都不会重复请求。
"""
from time import time

from . import client, config

_CACHE = {}                         # {vid|cid: (取到的时间, 地址)}
_CACHE_MAX = 200                    # 只是防内存无限涨,不是容量规划
_FAIL = {"reason": "", "msg": ""}   # 最近一次失败原因,给界面提示用


def api_base():
    """当前数据服务地址(末尾不带 /);未配置返回空串"""
    return client.base()


def _ttl():
    try:
        return max(0, int(getattr(config, "PLAY_API_CACHE", 60) or 0))
    except Exception:
        return 60


def _cache_get(key):
    _t = _ttl()
    if not _t:
        return ""
    _hit = _CACHE.get(key)
    if not _hit:
        return ""
    if time() - _hit[0] > _t:
        _CACHE.pop(key, None)
        return ""
    return str(_hit[1] or "")


def _cache_put(key, url):
    _t = _ttl()
    if not _t or not url:
        return
    if len(_CACHE) >= _CACHE_MAX:
        _now = time()
        for _k in [_k for _k, _v in _CACHE.items() if _now - _v[0] > _t]:
            _CACHE.pop(_k, None)
        if len(_CACHE) >= _CACHE_MAX:
            _CACHE.clear()
    _CACHE[key] = (time(), str(url))


def last_fail():
    """最近一次"没取到地址"的 (原因码, 说明);没失败过则都是空串"""
    return str(_FAIL.get("reason") or ""), str(_FAIL.get("msg") or "")


def _fail(reason, msg):
    _FAIL["reason"], _FAIL["msg"] = str(reason or ""), str(msg or "")
    return {"url": "", "source": "", "reason": _FAIL["reason"], "msg": _FAIL["msg"]}


def resolve(media_id, cid="", timeout=None):
    """取真实播放地址:返回 {"url","source","reason","msg"};url 为空即失败

    media_id 可以是 vid;cid 是剧集 id(剧集内某一集必须带上,cookie/referer 才对)。
    """
    _v = str(media_id or "").strip()
    if not _v:
        return _fail("none", "")
    _c = str(cid or "").strip()
    _key = "%s|%s" % (_v, _c)
    _hit = _cache_get(_key)
    if _hit:
        return {"url": _hit, "source": "cache", "reason": "", "msg": ""}
    _j = client.request_json("/play", {"vid": _v, "cid": _c}, t=timeout, default=None)
    if not isinstance(_j, dict):
        return _fail("none", "数据服务没应答: %s(数据源服务起了吗?地址对不对见 vgapi.PLAY_API_BASE)" % (api_base() or "(未配置)"))
    _u = str(_j.get("url") or "").strip()
    if not _u:
        _r = str(_j.get("reason") or "none")
        _m = str(_j.get("msg") or "")
        return _fail(_r, _m or ("服务端没取到地址(原因 %s)" % _r))
    _FAIL["reason"], _FAIL["msg"] = "", ""
    _cache_put(_key, _u)
    return {"url": _u, "source": str(_j.get("source") or "数据源"), "reason": "", "msg": ""}


def resolve_url(media_id, cid="", timeout=None):
    """只要地址;失败返回空串"""
    return str(resolve(media_id, cid, timeout=timeout).get("url") or "")


def health(timeout=5):
    """探测数据服务是否在线:返回 (是否在线, 说明文本)"""
    if not api_base():
        return False, "未配置数据服务地址(config/config.json 的 vgapi.PLAY_API_BASE)"
    _j = client.request_json("/health", t=timeout, default=None, quiet=True)
    if isinstance(_j, dict) and _j.get("ok"):
        return True, "%s(v%s / 取流后端 %s)" % (api_base(), _j.get("version") or "?",
                                                ",".join(_j.get("backends") or []) or "无")
    return False, "不可用(%s)" % api_base()
