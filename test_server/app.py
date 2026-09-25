# -*- coding: utf-8 -*-
"""测试数据源(HTTP 接口)

一个**不出网**的数据服务:把 tx_server/app.py 暴露的那套接口原样实现一遍,
响应的结构与字段名完全对齐(客户端 model/api/ 看到的是同一份形状),
但数据全部来自本地:目录见 catalog.py,占位封面见 cover.py,能真播的音轨见 tone.py。

它回答的是"这个客户端到底能不能装别的视频源"这个问题:
    config/config.json 的 vgapi.PLAY_API_BASE 改成 http://127.0.0.1:8790
    重新打开程序 → 轮播 / 搜索 / 选集 / 播放 / 弹幕 / 直播 全都照常,客户端零改动。

单独启动:
    python test_server/app.py                       # 默认 127.0.0.1:8790(tx_server 用 8765,两个可以同时开)
    python test_server/app.py --port 9000 --verbose
    python test_server/app.py --token secret        # 想顺带验一下口令走 X-Api-Token 的链路

接口(GET;浏览器直接打开就能验证;[鉴权] = 设了 --token 时必须带 token):
    # ---- 取流 ----
    GET /play?vid=<vid>[&cid=<剧集id>][&token=…]     → {"code":0,"url":"…/media/test.mp4?vg=1","source":"test-source"}
    GET /play?url=<…/cover/<剧集id>.html>            # 也认"详情页链接"这种写法
    # ---- 元数据 ----
    GET /episodes?cid=<剧集id>                       # 选集列表(与腾讯同构的 JSON 文本)
    GET /danmu?vid=<vid>                             # 弹幕/评论 → {"code":0,"data":[…]}
    GET /title?vid=<vid>&kind=video|play             # 片名 → {"code":0,"data":"…"}
    GET /vip_probe                                   # 会员探测 → {"code":0,"data":"<必定能播的 vid>"}
    # ---- 发现页 ----
    GET /search?q=<关键词>&page=1                    # 搜索结果(标准 JSON;不传 q 就按"测试"搜,搜不到会给全部条目兜底)
    GET /rotation?frequency=<频道号>                 # 轮播 → {"code":0,"pics":[],"names":[],"covers":[],"thumbs":[],
                                                     #        "bottoms":[{title,img,link},…],"keyword":"测试"}
    GET /hot_words                                   # 搜索热词
    GET /suggest?kw=<词>&field=word|tt               # 搜索联想词
    GET /image?url=<图片地址>                        # 图片代理:现算一张占位封面返回 PNG 字节
    # ---- 直播 ----
    GET /live      GET /migu_live                    # 直播频道表 → {"code":0,"data":{分类:[[地址,名,备注,封面],…]}}
    # ---- 媒体(给上面那些地址当目标用) ----
    GET /media/test.mp4                              # 可播放地址:test_server/media/ 里的那份测试视频(支持 Range)
    GET /media/stream                                # 同上(不指名时用"测试视频优先"挑一个;没有片源就现场合成音轨)
    GET /cover/<种子>.png                            # 占位封面本体(浏览器可直接看)
    GET /cover/<剧集id>.html                         # "详情页":客户端只从中抠剧集 id,人点开也能看见
    # ---- 其它 ----
    GET /health                                      # 健康检查
    GET /                                            # 本说明

想放真片源:把 mp4 / mkv / wav 丢进 test_server/media/ 即可(默认就用 test.mp4 这份测试视频),
/play 给的地址会自动指向它
(与真实数据源的差别只剩"内容从哪来"这一件事,取流后的播放链路完全相同)。
"""
import argparse
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from json import dumps
from urllib.parse import parse_qs, quote, unquote, urlparse

try:                                        # 作为包导入:from test_server.app import start_background
    from . import catalog
    from . import tone
    from . import cover as cover_png
except ImportError:                         # 直接运行:python test_server/app.py
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import catalog
    import tone
    import cover as cover_png

VERSION = "test-1.0"

_HERE = os.path.dirname(os.path.abspath(__file__))
_MEDIA_DIR = os.path.join(_HERE, "media")   # 放了真片源就用它;没有就用合成音轨
_TEST_VIDEO = "test.mp4"                    # 测试视频:取流地址默认直接指向它(见 _local_media)
_MEDIA_TYPES = {".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm",
                ".mkv": "video/x-matroska", ".mov": "video/quicktime",
                ".flv": "video/x-flv", ".ts": "video/mp2t",
                ".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
                ".aac": "audio/aac"}
_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8790                        # 与 tx_server 的 8765 错开,两份服务可以同时开着对比

_VERBOSE = False
_TOKEN = ""

_USAGE = ("VG 测试数据源 v%s\n"
          "\n"
          "一个不出网的数据服务:接口与 tx_server/ 一致,数据全在本地(见 test_server/catalog.py)。\n"
          "用法:把 config/config.json 的 vgapi.PLAY_API_BASE 指到本服务,客户端零改动即可跑通。\n"
          "\n"
          "取流:\n"
          "  GET /play?vid=<vid>&cid=<可选>\n"
          "  GET /play?url=<…/cover/剧集id.html>\n"
          "元数据:\n"
          "  GET /episodes?cid=<剧集id>\n"
          "  GET /danmu?vid=<vid>\n"
          "  GET /title?vid=<vid>&kind=video|play\n"
          "  GET /vip_probe\n"
          "发现页:\n"
          "  GET /search?q=<关键词>&page=1\n"
          "  GET /rotation?frequency=<频道号>\n"
          "  GET /hot_words\n"
          "  GET /suggest?kw=<词>&field=word|tt\n"
          "  GET /image?url=<图片地址>\n"
          "直播:\n"
          "  GET /live      GET /migu_live\n"
          "媒体:\n"
          "  GET /media/test.mp4    GET /media/stream      GET /cover/<种子>.png\n"
          "其它:\n"
          "  GET /health\n"
          "  GET /                                       本说明\n" % VERSION)


def _log(msg):
    print("[测试源 %s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


# ---------------------------------------------------------------- 媒体读取
def _read_file(path, start, end):
    """读文件的一段字节(供 Range 交付用);读不了就返回空"""
    try:
        with open(path, "rb") as _f:
            _f.seek(start)
            return _f.read(max(0, end - start + 1))
    except Exception:
        return b""


def _local_media(name=""):
    """test_server/media/ 里的片源 → (绝对路径, Content-Type)

    name 给了就只认这一个文件(/media/<文件名> 用它,找不到就是找不到);
    没给就按"测试视频优先"挑:先找 _TEST_VIDEO(test.mp4),再按文件名取第一个
    (/play 与 /media/stream 用它)。都没有返回 ("", "")。

    只认 media/ 目录里真实存在的文件名,所以 "../xxx" 这类越界名字压根不会命中。
    """
    try:
        _files = dict((_n, _MEDIA_TYPES.get(os.path.splitext(_n)[1].lower()))
                      for _n in sorted(os.listdir(_MEDIA_DIR))
                      if os.path.isfile(os.path.join(_MEDIA_DIR, _n)))
    except Exception:
        _files = {}
    _want = os.path.basename(str(name or "").strip())
    if _want:
        _ct = _files.get(_want)
        return (os.path.join(_MEDIA_DIR, _want), _ct) if _ct else ("", "")
    for _n in [_TEST_VIDEO] + sorted(_files):
        if _files.get(_n):
            return os.path.join(_MEDIA_DIR, _n), _files[_n]
    return "", ""


# ---------------------------------------------------------------- HTTP 层
class _Handler(BaseHTTPRequestHandler):
    server_version = "VGTestSource/" + VERSION
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):          # 默认日志太吵:只在 --verbose 下打
        if _VERBOSE:
            _log("%s %s" % (self.address_string(), fmt % args))

    # ---------------- 基础响应 ----------------
    def _send(self, status, body, ctype):
        _b = body if isinstance(body, bytes) else str(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(_b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(_b)
        except Exception:
            pass

    def _json(self, status, obj):
        self._send(status, dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

    def _ok(self, data):
        """统一成功响应:拿不到东西也算 200,用 code 区分(客户端就是按 code 判断的)"""
        return self._json(200, {"code": 0 if data else 1, "data": data})

    def _serve_block(self, total, ctype, read_at):
        """按 Range 交付一段字节(read_at(start, end) 返回该闭区间);能应答 200 / 206

        支持 Range 是必要的:播放器拖动进度条时会带 Range 重新要一段,
        不支持的话"能播但不能拖",看起来就像取流坏了。
        """
        _rng = str(self.headers.get("Range") or "").strip()
        _start, _end, _part = 0, max(0, total - 1), False
        if _rng.lower().startswith("bytes="):
            _spec = _rng[6:].split(",")[0].strip()
            _a, _, _b = _spec.partition("-")
            try:
                if _a:
                    _start = max(0, int(_a))
                    _end = min(total - 1, int(_b)) if _b else total - 1
                else:                                  # bytes=-N:要最后 N 字节
                    _start, _end = max(0, total - int(_b)), total - 1
                _part = _start <= _end
            except Exception:
                _start, _end, _part = 0, max(0, total - 1), False
        if not _part:
            _start, _end = 0, max(0, total - 1)
        _body = read_at(_start, _end)
        self.send_response(206 if _part else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(_body)))
        self.send_header("Accept-Ranges", "bytes")
        if _part:
            self.send_header("Content-Range", "bytes %d-%d/%d" % (_start, _end, total))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(_body)
        except Exception:
            pass

    # ---------------- 地址 / 标记翻译 ----------------
    def _base(self):
        """本服务的对外地址:优先用请求里的 Host(客户端怎么找过来的就怎么回去),退回监听地址"""
        _h = str(self.headers.get("Host") or "").strip()
        if not _h:
            _h = "%s:%d" % (self.server.server_address[0], self.server.server_address[1])
        return "http://" + _h

    def _pub_img(self, token):
        """把目录里的图片标记翻成绝对地址

        这里必须翻成**真正的 URL**:客户端 fetch_image 见到字符串里没有 "://" 时,
        会把它当成"本地文件路径"直接交给 PIL 打开 —— 所以 "cover:xxx" 这种标记
        只能存在于服务端内部,发给客户端的必须是 http://…/cover/xxx.png。
        """
        _v = str(token or "")
        if _v.startswith("cover:"):
            return "%s/cover/%s.png" % (self._base(), quote(_v[6:], safe=""))
        return _v

    def _pub_page(self, token):
        """把"详情页链接"标记翻成绝对地址:客户端点推荐位时会从链接末尾抠出剧集 id"""
        _v = str(token or "")
        if _v.startswith("drama:"):
            return "%s/cover/%s.html" % (self._base(), quote(_v[6:], safe=""))
        return _v

    def _media_addr(self, name=""):
        """片源地址:有真片源就指到那个文件(默认 test.mp4),没有就指 /media/stream(合成音轨)

        指到具体文件名是有意的:播放器拿到的就是"那个测试视频",
        /media/<文件名> 同样支持 Range,拖动进度条的链路跟 /media/stream 一模一样。

        末尾必须带一个 query(这里用 ?vg=1):
        客户端拿到地址后会拼成 "<地址>&<单集id>=vg" 再交给播放器(见 view/player/*),
        地址里没有 "?" 时这个尾巴会粘在路径上(/media/test.mp4&tstc0001_v001=vg),
        服务端就按不存在的路径 404 了 —— 播放器什么也放不出来。
        带上 ?vg=1 后拼出来的仍是合法 URL,路径干净,而且客户端还能从末尾反解出单集 id。
        """
        _f, _ct = _local_media(name)
        if _f:
            return "%s/media/%s?vg=1" % (self._base(), quote(os.path.basename(_f), safe=""))
        return "%s/media/stream?vg=1" % self._base()

    def _pub_addr(self, token):
        """播放地址标记:stream → 本服务的片源地址(有测试视频就指到那个文件)"""
        return self._media_addr() if str(token or "") == "stream" else str(token or "")

    @staticmethod
    def _seed_of(url):
        """从客户端递过来的图片地址里抠出封面种子

        客户端是把 img 原样塞进 /image?url= 的,所以这里可能是:
            http://任意主机/cover/<种子>.png   ← 正常情况(主机名不重要,只认路径)
            cover:<种子>                       ← 手工调接口时会这么写
        两种都认,认不出来返回空串。
        """
        _u = str(url or "").strip()
        _m = re.search(r"/cover/([^/]+)\.png$", urlparse(_u).path or "")
        if _m:
            return unquote(_m.group(1))
        return _u[6:] if _u.startswith("cover:") else ""

    # ---------------- 路由 ----------------
    def do_GET(self):
        _u = urlparse(self.path)
        _path = (_u.path or "/").rstrip("/") or "/"
        if _path == "/health":
            return self._json(200, {"code": 0, "ok": True, "version": VERSION,
                                    "backends": ["test-source"], "url_ttl": 0})
        if _path == "/":
            return self._send(200, _USAGE, "text/plain; charset=utf-8")
        _q = parse_qs(_u.query, keep_blank_values=True)

        def _one(_k):
            return (_q.get(_k) or [""])[0].strip()

        def _int(_k, _d=0):
            try:
                return int(_one(_k) or _d)
            except Exception:
                return _d

        # ---- 鉴权:与 tx_server 同一套(带头或地址里带都行) ----
        _token = _one("token") or str(self.headers.get("X-Api-Token") or "").strip()
        if _TOKEN and _token != _TOKEN:
            return self._json(401, {"code": 1, "msg": "invalid token"})

        # ---- 图片:现算一张占位封面(不读磁盘、不联网) ----
        if _path == "/image":
            _seed = self._seed_of(_one("url"))
            if not _seed:
                return self._json(404, {"code": 1, "msg": "不是本测试源的图片地址(要 …/cover/<种子>.png)"})
            return self._send(200, cover_png.png(_seed), "image/png")

        # ---- 媒体:/media/<文件名> 指名要哪个片源(test.mp4 就是那份测试视频);
        #          /media/stream 走"测试视频优先"的挑选;都没有就合成音轨(都支持 Range) ----
        if _path.startswith("/media/"):
            # 客户端会把地址拼成 "<地址>&<单集id>=vg" 再交给播放器;没有 ? 时这段尾巴会落在 path 里,
            # 所以这里只取 "&" / "?" 前面的文件名(再 basename 一次,顺手挡掉 "../" 这类写法)。
            _name = os.path.basename(unquote(_path[len("/media/"):]).split("&")[0].split("?")[0].strip())
            _f, _ct = _local_media("" if _name == "stream" else _name)
            if _f:
                return self._serve_block(os.path.getsize(_f), _ct,
                                         lambda _s, _e: _read_file(_f, _s, _e))
            if not _name or _name == "stream":
                _b = tone.wav()
                return self._serve_block(len(_b), "audio/wav", lambda _s, _e: _b[_s:_e])
            return self._json(404, {"code": 1, "msg": "media 里没有这个片源:%s" % _name})

        # ---- 占位封面本体(给人用浏览器直接看) ----
        if _path.startswith("/cover/") and _path.endswith(".png"):
            return self._send(200, cover_png.png(unquote(_path[7:-4])), "image/png")

        # ---- "详情页"(客户端只抠 id,人点开也看得见内容) ----
        if _path.startswith("/cover/") and _path.endswith(".html"):
            return self._drama_page(unquote(_path[7:-5]))

        # ---- 取流:数据源里所有能播的 id 都指向同一个本地媒体 ----
        if _path == "/play":
            return self._play(_one("vid"), _one("cid"), _one("url"))

        if _path == "/episodes":                     # 客户端要的就是这份 JSON 文本,原样给它
            return self._send(200, catalog.episodes(_one("cid")),
                              "application/json; charset=utf-8")
        if _path == "/danmu":
            return self._ok(catalog.danmu(_one("vid")))
        if _path == "/title":
            return self._ok(catalog.title(_one("vid")))
        if _path == "/vip_probe":
            return self._ok(catalog.vip_probe())
        if _path == "/search":
            return self._ok(self._pub_search(catalog.search(_one("q"), _int("page", 1))))
        if _path == "/rotation":
            _p, _n, _c, _t = catalog.rotation()
            _p = [self._pub_img(_x) for _x in _p]
            _t = [self._pub_img(_x) for _x in _t]
            _c = [self._pub_page(_x) for _x in _c]
            # bottoms:首页底部那一排推荐位(与大轮播同一批测试图 / 测试名)
            _b = [{"title": _x["title"], "img": self._pub_img(_x["img"]),
                   "link": self._pub_page(_x["link"])} for _x in catalog.bottoms()]
            return self._json(200, {"code": 0 if _p else 1,
                                    "pics": _p, "names": _n, "covers": _c, "thumbs": _t,
                                    "bottoms": _b, "keyword": catalog.default_keyword()})
        if _path == "/hot_words":
            return self._ok(catalog.hot_words())
        if _path == "/suggest":
            return self._ok(catalog.suggest(_one("kw")))
        if _path == "/live" or _path == "/migu_live":
            return self._ok(self._pub_live(catalog.live()))
        return self._json(404, {"code": 1, "msg": "not found"})

    # ---------------- 各接口的组装 ----------------
    def _pub_search(self, data):
        """把搜索结果里的 img 标记翻成客户端能请求的绝对地址(其余字段原样)"""
        for _it in data.get("items") or []:
            _it["img"] = self._pub_img(_it.get("img"))
        return data

    def _pub_live(self, groups):
        """直播频道表:[地址, 名称, 备注, 封面] 里的地址与封面都要翻成绝对地址"""
        for _rows in groups.values():
            for _row in _rows:
                if len(_row) >= 4:
                    _row[0], _row[3] = self._pub_addr(_row[0]), self._pub_img(_row[3])
        return groups

    def _play(self, vid, cid, url):
        """/play:认识这个 id 就给本地媒体地址,不认识就照实说(客户端会显示失败原因)"""
        _id = str(vid or cid or "").strip()
        if not _id and url:                          # 也认"详情页链接":从末尾抠出剧集 id
            _m = re.search(r"/cover/([^/]+)\.html$", urlparse(str(url)).path or "")
            _id = unquote(_m.group(1)) if _m else str(url).strip()
        if not catalog.is_known(_id):
            return self._json(200, {"code": 1, "url": "", "source": "", "reason": "none",
                                    "msg": "测试数据源里没有这个 id:%s(可用 id 见 GET / 或 GET /search)"
                                           % (_id or "(空)")})
        _f, _ct = _local_media()                     # 测试场景:播的就是 media/ 里那份测试视频
        return self._json(200, {"code": 0, "url": self._media_addr(),
                                "source": "test-source", "cached": 0,
                                "media": os.path.basename(_f) if _f else ""})

    def _drama_page(self, cid):
        """"详情页":客户端不请求它(只从链接里抠 id),人用浏览器打开时至少能看见内容"""
        _it = catalog.find_cover(cid)
        if not _it:
            return self._json(404, {"code": 1, "msg": "没有这个剧集:%s" % cid})
        _eps = "".join("<li>%s &nbsp;<code>%s</code></li>" % (_e["title"], _e["id"])
                       for _e in _it["episodes"])
        _html = ("<!doctype html><meta charset='utf-8'><title>%s</title>"
                 "<body style='font:14px/1.7 system-ui;background:#16181d;color:#ddd;padding:24px'>"
                 "<h2>%s</h2><p>%s</p><p>剧集 id:<code>%s</code>(共 %d 集)</p>"
                 "<ol>%s</ol>"
                 "<p style='color:#888'>这是 test_server 生成的占位详情页;"
                 "播放地址:/play?vid=&lt;单集id&gt;</p></body>"
                 % (_it["title"], _it["title"], _it["desc"], _it["id"],
                    len(_it["episodes"]), _eps))
        return self._send(200, _html, "text/html; charset=utf-8")


# ---------------------------------------------------------------- 启动
def build_server(host=None, port=None):
    """建一个 HTTP 服务对象(不启动);建不起来直接抛异常,由调用方决定怎么处理"""
    _h = str(host or _DEFAULT_HOST)
    _p = int(port or _DEFAULT_PORT)
    _srv = ThreadingHTTPServer((_h, _p), _Handler)
    _srv.daemon_threads = True
    return _srv


def start_background(host=None, port=None, quiet=False, token=""):
    """后台线程起一份服务(给自动化测试 / 冒烟脚本用;正常使用是命令行直接跑 app.py)

    端口被占用 / 环境不允许时只打印一行提示并返回 None —— 绝不抛异常、绝不阻塞启动。
    """
    global _TOKEN
    _TOKEN = str(token or "")
    try:
        _srv = build_server(host, port)
    except Exception as _e:
        _log("未启动(%s:%s 不可用):%s" % (host or _DEFAULT_HOST, port or _DEFAULT_PORT, _e))
        return None
    threading.Thread(target=_srv.serve_forever, name="testsource-http", daemon=True).start()
    if not quiet:
        _h = str(host or _DEFAULT_HOST)
        _log("已启动: http://%s:%s/(把 vgapi.PLAY_API_BASE 改成它即可)" %
             ("127.0.0.1" if _h == "0.0.0.0" else _h, int(port or _DEFAULT_PORT)))
    return _srv


def main(argv=None):
    global _VERBOSE, _TOKEN
    _ap = argparse.ArgumentParser(description="VG 测试数据源(不出网,数据全在本地)")
    _ap.add_argument("--host", default=_DEFAULT_HOST, help="监听地址,默认 127.0.0.1")
    _ap.add_argument("--port", type=int, default=_DEFAULT_PORT, help="监听端口,默认 8790")
    _ap.add_argument("--token", default="", help="设定口令(设了就必须带 ?token= 或 X-Api-Token)")
    _ap.add_argument("--verbose", action="store_true", help="打印每个请求的访问日志")
    _a = _ap.parse_args(argv)
    _VERBOSE = bool(_a.verbose)
    _TOKEN = str(_a.token or "")
    try:
        _srv = build_server(_a.host, _a.port)
    except Exception as _e:
        _log("启动失败(%s:%s):%s" % (_a.host, _a.port, _e))
        return 1
    _f, _ct = _local_media()
    _log("VG 测试数据源 v%s 已启动: http://%s:%s/" % (VERSION, _a.host, _a.port))
    _log("媒体来源:%s" % ("test_server/media/%s(%s)" % (os.path.basename(_f), _ct)
                          if _f else "现场合成音轨(往 test_server/media/ 丢个 mp4 就会换成它)"))
    _log("把 config/config.json 的 vgapi.PLAY_API_BASE 改成 http://%s:%s 再打开客户端即可"
         % ("127.0.0.1" if _a.host == "0.0.0.0" else _a.host, _a.port))
    try:
        _srv.serve_forever()
    except KeyboardInterrupt:
        _log("收到 Ctrl+C,退出")
    finally:
        _srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
