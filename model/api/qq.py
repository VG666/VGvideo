# -*- coding: utf-8 -*-
"""数据源数据接口(model.api.qq)—— 只负责"向数据服务要数据"

本文件里凡是**要出网**的函数,实现清一色是"转调":拼参数 → 发一次 HTTP 给数据服务(数据源项目),
真正取数的逻辑在服务端(数据源项目的 sources/meta.py)。客户端不直连数据源域名,也不自带本机解析。
    GET /episodes?cid=          选集(原样回传数据源的 JSON 文本)
    GET /danmu?vid=             弹幕
    GET /title?vid=&kind=       片名(kind=video 下载命名用 / kind=play 播放页显示用)
    GET /vip_probe              会员专属片探测

留在本文件里的只剩"纯本地"的几个小工具(不联网):播放页链接 → vid、集号排序、从 JSON 文本取标题。
取流入口照旧(内部转调 remote,地址同样来自数据服务):
    _resolve_url       只要地址,失败返回空串(老写法,行为不变)
    _resolve_url_info  要完整结果 {"url","source","reason","msg"}:reason=drm 表示内容加密(取得到但本机播不了)
    play_fail_msg      最近一次失败的说明,供界面提示"为什么放不了"

所有函数都"失败返回空值、不抛异常",保证界面不会因为网络问题崩掉。
"""
import re

from . import client, config
from .util import _json_load


def _qq_is_web_page(u):  # 是数据源的网页地址(播放页),不是能直接播的流地址
    _s = str(u or "").strip().lower()
    if "://" not in _s:
        return False
    _m = re.match(r"https?://([^/?#]+)", _s)
    _host = (_m.group(1) if _m else "").split(":")[0]
    return (".html" in _s) or _host.endswith(".qq.com")


def _qq_url_to_vid(url):  # 播放页链接 → vid(对应 TXSP.py 的 get_vid);抠不到返回空串
    # 注意:只认 /x/page/<vid>.html 与 /x/cover/<cid>/<vid>.html 这类"带上 vid"的形式;
    #       /x/cover/<cid>.html 里那个是剧集 id(拿来取流必失败),要交给选集流程处理,这里返回空串。
    #       vid 固定 11 位,但 cid 长度不定(如 mzc00200w9qrf4g 有 15 位),所以不能拿 {11} 一刀切。
    _s = str(url or "").strip()
    if not _s or "://" not in _s:
        return ""
    for _p in (r"/page/([A-Za-z0-9_-]{6,32})",                       # 单视频页
               r"/cover/[A-Za-z0-9_-]{6,32}/([A-Za-z0-9_-]{6,32})",  # 剧集页里的某一集
               r"[?&]vid=([A-Za-z0-9_-]{6,32})"):                    # 带 ?vid= 的地址
        _m = re.search(_p, _s)
        if _m:
            return _m.group(1)
    return ""


def _resolve_url_info(media_id, cid=""):  # 取真实播放地址(带失败原因):返回 {"url","source","reason","msg"};url 为空即失败
    # 本文件只管"入参归一化 + 转调",取流本身由 remote 向数据服务要:
    #   0) 规范化:播放页链接 → vid;已经是流地址(直播/外部流) → 原样返回
    #   1) remote.resolve:vid(+cid) → 真实播放地址 + 失败原因
    _none = {"url": "", "source": "", "reason": "none", "msg": ""}
    _v = str(media_id or "").strip()
    if not _v:
        return _none
    if "://" in _v:
        if not _qq_is_web_page(_v):
            return {"url": _v, "source": "direct", "reason": "", "msg": ""}   # 直播 / 外部流:本来就是能直接播的地址
        _v = _qq_url_to_vid(_v)       # 播放页链接:先抠出 vid(原来直接原样返回,等于把网页地址丢给播放器)
        if not _v:
            return _none
    try:
        from .remote import resolve as _remote_resolve
        _r = _remote_resolve(_v, cid or _qq_cover_id()) or {}
        return {"url": str(_r.get("url") or ""), "source": str(_r.get("source") or ""),
                "reason": str(_r.get("reason") or ""), "msg": str(_r.get("msg") or "")}
    except Exception as _e:                 # 服务端连不上 / 返回异常:按"取不到"处理
        print("取流接口调用失败:", _e)
        return _none


def _resolve_url(media_id, cid=""):  # 取真实播放地址(对外唯一入口):入参可以是 vid,也可以是播放页链接;失败返回空串
    return str(_resolve_url_info(media_id, cid).get("url") or "")


def play_fail_msg():  # 最近一次"没取到地址"的说明(如"该内容是加密视频…"),供界面提示;成功或没解析过时返回空串
    try:
        from .remote import last_fail as _last_fail
        return str(_last_fail()[1] or "")
    except Exception:
        return ""


def _qq_cover_id():  # 当前若是剧集播放(App 模式2)则返回剧集 cid,否则空串(纯读本地启动参数,不涉及网络)
    try:
        _argv = config.main_argv()
        if str(_argv[1]) == "2":
            _a = str(_argv[2] or "").strip()
            if re.fullmatch(r"[A-Za-z0-9_-]{6,32}", _a):
                return _a
    except Exception:
        pass
    return ""


def _qq_ep_no(v):  # 从"001"/"第7集 xx"/"1"里抠集号数字;抠不到给大值(排到最后)
    try:
        _m = re.search(r"\d+", str(v or ""))
        return int(_m.group(0)) if _m else 10 ** 9
    except Exception:
        return 10 ** 9


# ---------------------------------------------------------------- 以下一律转调数据服务
def _qq_episodes(cid):  # 取剧集选集:数据服务汇总后,回一份内置播放器可直接吃的 JSON 文本;失败返回空串
    # 返回结构与旧 get_playsource 同构(PlaylistItem/videoPlayList),因此选集界面/高亮/续播逻辑无需改动
    _c = str(cid or "").strip()
    if not _c:
        return ""
    return client.request_text("/episodes", {"cid": _c}, default="")


def _qq_ep_title(txt, i):  # 从剧集 JSON 取第 i 集显示名(play_title 形如"斗罗大陆Ⅱ绝世唐门 第001话");失败返回空串
    try:
        _pl = ((_json_load(txt).get("PlaylistItem") or {}).get("videoPlayList")) or []
        _it = _pl[int(i)] if 0 <= int(i) < len(_pl) else {}
        return str(_it.get("title") or "").strip() or str(_it.get("episode_number") or "").strip()
    except Exception:
        return ""


def _qq_danmu(vid):  # 取该 vid 的真实弹幕(含点赞数),按点赞降序;网页评论区已下线,用它承载"评论"页;失败返回 []
    _v = str(vid or "").strip()
    if not _v:
        return []
    _out = []
    for _c in (client.request_json("/danmu", {"vid": _v}, default=[]) or []):
        if not isinstance(_c, dict):
            continue
        _t = str(_c.get("content") or "").strip()
        if not _t:
            continue
        try:
            _up = int(_c.get("up") or 0)
        except Exception:
            _up = 0
        _out.append({"content": _t, "up": _up, "time": _c.get("time") or 0})
    _out.sort(key=lambda _x: _x["up"], reverse=True)   # 服务端已排过一遍,这里只做防御性归一
    return _out


def _qq_video_title(vid):  # 下载时给文件命名:片名走数据服务(服务端裸请求 getinfo 取 ti);失败返回空串
    _v = str(vid or "").strip()
    if not _v:
        return ""
    return str(client.request_json("/title", {"vid": _v, "kind": "video"}, default="") or "").strip()


def _qq_play_title(vid):  # 播放页显示片名:走数据服务(服务端带 Cookie/Referer 取 ti);失败返回空串
    _v = str(vid or "").strip()
    if not _v:
        return ""
    return str(client.request_json("/title", {"vid": _v, "kind": "play"}, default="") or "").strip()


def _qq_vip_probe():  # 未收录/VIP 内容兜底:数据服务探测接口给出的推荐 vid;取不到返回空串
    return str(client.request_json("/vip_probe", default="") or "").strip()
