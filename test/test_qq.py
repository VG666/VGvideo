# -*- coding: utf-8 -*-
"""数据源接口自测脚本(客户端接口 + 数据服务端到端;取流平台号统一写死 11)。

取数本体已从客户端下沉到数据服务(tx_server/),所以本脚本分两段测:
    客户端:纯函数 / 选集 / 弹幕 / 标题 / 源码回归(不再有取流与第三方抓取);
    服务端:数据服务探活 + _resolve_url 端到端(地址实测可取)+ 服务端取流后端回归。

用法:
    python test/test_qq.py                  # 用内置默认 vid / cid
    python test/test_qq.py <vid> <cid>      # 指定被测视频与剧集

判定约定:
    PASS = 断言通过
    FAIL = 行为不符合预期(返回体格式错、排序乱、字段缺失、源码里残留旧平台号等),脚本退出码 1
    SKIP = 依赖网络 / 会员权益 / 数据服务,当前拿不到数据,只记录不判失败

注意:第 5 项对会员集可能拿不到地址(11 只返回裸前缀),这属于权益限制而非 bug,故记 SKIP。
      客户端不再自建服务:跑本脚本前请先起数据服务(python tx_server/app.py,默认 127.0.0.1:8765);
      服务不可用时第 4 项记 SKIP,其余依赖它的项同样跳过。
"""
import sys, io, re, os, glob
from json import dumps

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 本脚本收在 test/ 里,程序目录(根)才是 import main 的来源
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    import main as video    # 程序入口已改名 main.py;本脚本沿用 video 这个别名(下面 video.xxx 都指它)
except Exception as _e:
    print("导入 main 失败: %s" % _e)
    sys.exit(2)

VID = (sys.argv[1] if len(sys.argv) > 1 else "i0046sewh4r").strip()   # 默认:斗罗大陆2绝世唐门 第001集
CID = (sys.argv[2] if len(sys.argv) > 2 else "mzc00200xf3rir6").strip()  # 默认对应剧集 cid

_P, _F, _S = [], [], []


def check(name, cond, detail=""):
    (_P if cond else _F).append(name)
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name, ("  -> " + detail) if detail else ""))


def skip(name, why=""):
    _S.append(name)
    print("  [SKIP] %s%s" % (name, ("  -> " + why) if why else ""))


def head(t):
    print("\n=== %s ===" % t)


def _probe(u, n=1024):
    """实取 1KB 验证地址真的能取到(替代已下沉服务端的 _url_ok)"""
    try:
        from urllib.request import Request, urlopen
        _r = urlopen(Request(str(u), headers={"User-Agent": "VGVideo/1.0",
                                             "Range": "bytes=0-%d" % (n - 1)}), timeout=8)
        return bool(_r.read(n))
    except Exception:
        return False


# ---------- 1. 纯函数(不联网,失败即真 bug) ----------
head("1. 纯函数")
for _raw in ('QZOutputJson={"a":1};', '{"a":1}', '  {"a":1}  '):
    _j = video._json_load(_raw)
    check("_json_load 解析 %r" % _raw[:24], _j.get("a") == 1, str(_j))
check("_json_load 空串返回 {}", video._json_load("") == {})
check("_json_load 垃圾串不抛异常", video._json_load("not json at all") == {})

for _v, _want in (("001", 1), ("12", 12), ("第7集 斗破苍穹", 7), ("预告片", 10 ** 9), ("", 10 ** 9)):
    _got = video._qq_ep_no(_v)
    check("_qq_ep_no(%r) == %s" % (_v, _want), _got == _want, "got %s" % _got)

_txt = dumps({"PlaylistItem": {"title": "斗罗大陆Ⅱ绝世唐门", "videoPlayList": [
    {"id": "a1", "episode_number": "001", "title": "斗罗大陆Ⅱ绝世唐门 第001话", "playUrl": "", "markLabelList": []},
    {"id": "a2", "episode_number": "第2集", "title": "", "playUrl": "", "markLabelList": []}]}})
check("_qq_ep_title 取 title", video._qq_ep_title(_txt, 0) == "斗罗大陆Ⅱ绝世唐门 第001话", video._qq_ep_title(_txt, 0))
check("_qq_ep_title title 为空时回退集号", video._qq_ep_title(_txt, 1) == "第2集", video._qq_ep_title(_txt, 1))
check("_qq_ep_title 越界返回空串不抛异常", video._qq_ep_title(_txt, 99) == "", repr(video._qq_ep_title(_txt, 99)))
for _u, _want in (("https://v.qq.com/x/page/r0047gdjpw6.html", "r0047gdjpw6"),
                  ("https://v.qq.com/x/cover/mzc00200xf3rir6/i0046sewh4r.html", "i0046sewh4r"),
                  ("https://v.qq.com/x/cover/mzc00200xf3rir6.html", ""),   # 只有剧集 id:要交给选集流程,不能当 vid
                  ("这不是地址", "")):
    _got = video._qq_url_to_vid(_u)
    check("_qq_url_to_vid(…%s)" % _u[-30:], _got == _want, "got %r" % _got)
check("_qq_is_web_page 认播放页", video._qq_is_web_page("https://v.qq.com/x/page/r0047gdjpw6.html") is True)
check("_qq_is_web_page 不认流地址", video._qq_is_web_page("http://1.2.3.4/live.m3u8") is False)

# ---------- 2. 源码回归:平台号统一写死 11(model/api 除外);取流只在服务端 ----------
head("2. 源码回归:取流平台号写死 11(服务端);客户端不再自带第三方抓取")


def _read_src(*dirs):
    """把一个或多个目录下的 .py 拼成一份源码文本(读不到的忽略)"""
    _s = ""
    for _d in dirs:
        for _p in glob.glob(os.path.join(_d, "**", "*.py"), recursive=True):
            try:
                _s += open(_p, "r", encoding="utf-8", errors="replace").read()
            except Exception:
                pass
    return _s


_vroot = os.path.dirname(os.path.abspath(video.__file__))                     # 程序目录(根)
_api_dir = os.path.join(_vroot, "model", "api")
_src = _read_src(_api_dir)                                                    # 客户端 model/api 全量源码
# 做"域名回归"时排除 config.py:它只是配置(里面有参考用 Referer 之类的地址),不是"获取实现"
_src_code = "".join(open(_p, "r", encoding="utf-8", errors="replace").read()
                    for _p in glob.glob(os.path.join(_api_dir, "*.py"))
                    if os.path.basename(_p) != "config.py")
_srv_stream = _read_src(os.path.join(_vroot, "tx_server", "vgplay"))             # 服务端:取流本体
_srv_src = _read_src(os.path.join(_vroot, "tx_server", "sources"))               # 服务端:各数据源(选集/标题/搜索…)
_srv = _srv_stream + _srv_src
_TITLE_TPL = "platform=10801&otype=ojson&sdtfrom=v4138&appVer=7&vid="
if not _src or not _srv:
    skip("读取源码", "客户端 %d 字符 / 服务端 %d 字符" % (len(_src), len(_srv)))
else:
    check('服务端取流源码内不存在 platform=10801', "platform=10801" not in _srv_stream)
    check('服务端取流源码内不存在 platform=11001', "platform=11001" not in _srv_stream)
    check('服务端取流源码内不存在 platform=10201', "platform=10201" not in _srv_stream)
    _m = (re.findall(r"platform=(\d+)", _srv_stream)
          + re.findall(r"platform\s*=\s*['\"](\d+)['\"]", _srv_stream, re.I))
    check("服务端取流平台号全部是 11(getinfo / vinfo / ckey)", bool(_m) and all(x == "11" for x in _m),
          str(sorted(set(_m))))
    # 标题接口(10801 模板)已随取流一起下沉:服务端该有,客户端不该再有
    check("标题接口模板已下沉到服务端", _TITLE_TPL in _srv_src)
    check("客户端不再自带标题接口实现", _TITLE_TPL not in _src_code)
    # "api 文件夹只用来获取":不该再出现任何第三方域名,出网只能有 client.py 一个口子
    _bad = sorted({_h for _h in re.findall(r"https?://([A-Za-z0-9.\-]+)", _src_code)
                   if ("qq.com" in _h or "qpic.cn" in _h or "gtimg.cn" in _h or "migu" in _h)})
    check("model/api 不再直连第三方域名(数据只从数据服务取)", not _bad, str(_bad))
    _net = sorted(os.path.basename(_p) for _p in glob.glob(os.path.join(_api_dir, "*.py"))
                  if "urlopen(" in open(_p, "r", encoding="utf-8", errors="replace").read())
    check("客户端唯一出网口是 client.py", _net == ["client.py"], str(_net))
check("客户端已无取流工具属性(_url_ok / _force_http)",
      not hasattr(video, "_url_ok") and not hasattr(video, "_force_http"))
check("客户端已无取流函数属性(_qq_getinfo / qqvideo)",
      not hasattr(video, "_qq_getinfo") and not hasattr(video, "qqvideo"))

# ---------- 3. 数据服务探活(取流已下沉;客户端不再自建服务,只探活) ----------
head("3. 数据服务探活 /health")
print("     数据源: %s" % video.source_line())
_srv_ok, _srv_why = False, "健康检查异常"
try:
    _srv_ok, _srv_why = video.play_api_health()
except Exception as _e:
    _srv_why = "健康检查异常: %s" % _e
if _srv_ok:
    check("数据服务在线", True, _srv_why)
else:
    skip("数据服务在线", "%s(请先 python tx_server/app.py;第 4 项跳过)" % _srv_why)

# ---------- 4. 端到端:客户端唯一取流入口 _resolve_url ----------
head("4. _resolve_url 端到端(数据服务)")
if not _srv_ok:
    skip("解析播放地址", "数据服务不可用")
else:
    _url = video._resolve_url(VID)
    if not _url:
        skip("解析播放地址", "服务端各后端都没取到(会员 / DRM / 网络)")
    else:
        check("返回 http(s) 地址(不能是 HTML/纯文本)", bool(re.match(r"^https?://", _url)), _url[:110])
        check("地址实测可取(取 1KB)", _probe(_url), _url[:110])

# ---------- 5. 服务端取流后端回归(getinfo / qqvideo 兼容写法) ----------
head("5. 服务端取流后端回归")
try:
    from tx_tx_server.vgplay import qq as _sqq        # 取流本体已下沉到 tx_server/vgplay
except Exception as _e:
    _sqq = None
    skip("导入服务端取流模块", str(_e))
if _sqq is not None:
    _hls = _sqq._qq_getinfo(VID, "10800")
    if not _hls:
        skip("服务端 getinfo HLS", "该 vid 只返回 CDN 裸前缀(会员/DRM)或网络失败")
    else:
        check("HLS 地址是 http(s)", _hls.startswith("http"), _hls[:110])
        check("已过滤以 / 结尾的裸前缀", not _hls.endswith("/"), _hls[:110])
    _mp4 = _sqq._qq_getinfo(VID, "720", "shd") or _sqq._qq_getinfo(VID, "720")
    if not _mp4:
        skip("服务端 getinfo MP4", "无 MP4 流(会员集常见)或网络失败")
    else:
        check("MP4 地址是 http(s)", _mp4.startswith("http"), _mp4[:110])
        check("不是以 / 结尾的目录前缀", not _mp4.endswith("/"), _mp4[:110])
    # 注意:getinfo 每次返回的地址都带独立签名(vkey),两次调用的字符串必然不同,只能校验“是否可用”,不能比对相等
    for _k in ("10800", "720"):
        _r5 = _sqq.qqvideo(VID, _k)
        if not _r5:
            skip("服务端 qqvideo(vid,%r)" % _k, "本次未取到地址(与 getinfo 同源,权益/网络限制)")
        else:
            check("服务端 qqvideo(vid,%r) 返回可用地址" % _k,
                  _r5.startswith("http") and not _r5.endswith("/"), _r5[:90])
    check("未知 vid 返回空串不抛异常",
          _sqq.qqvideo("", "10800") == "" and _sqq.qqvideo("zzzzzzzz", "10800") == "")

# ---------- 6. 标题接口(下载文件名 / 播放器标题依赖;实现已在服务端) ----------
head("6. 标题接口(GET /title,服务端 platform=10801 + otype=ojson)")
_ti = video._qq_video_title(VID)
if not _ti:
    skip("标题 ti 字段", "数据服务没取到(网络失败 / 服务未启动)")
else:
    check("下载命名用片名非空", bool(_ti.strip()), _ti)
    _ti2 = video._qq_play_title(VID)
    if _ti2:
        check("播放页片名非空", bool(_ti2.strip()), _ti2)
    else:
        skip("播放页片名", "数据服务本次未取到(与下载片名同源)")

# ---------- 7. 选集 ----------
head("7. _qq_episodes 选集")
_pl = []
_raw = video._qq_episodes(CID)
if not _raw:
    skip("选集 JSON", "接口无返回(网络失败或 cid 失效)")
else:
    _j = video._json_load(_raw)
    _pi = _j.get("PlaylistItem") or {}
    _pl = _pi.get("videoPlayList") or []
    check("PlaylistItem.videoPlayList 非空", bool(_pl), "集数 %d" % len(_pl))
    check("剧名非空", bool(str(_pi.get("title") or "").strip()), str(_pi.get("title")))
    if _pl:
        check("每项都有 id / episode_number", all(x.get("id") and x.get("episode_number") for x in _pl))
        check("每项都有 playUrl / markLabelList 字段", all("playUrl" in x and "markLabelList" in x for x in _pl))
        _nos = [video._qq_ep_no(x["episode_number"]) for x in _pl]
        check("按集号升序(第1集在最前)", _nos == sorted(_nos), str(_nos[:10]))
        _ids = {x["id"] for x in _pl}
        check("vid 无重复", len(_ids) == len(_pl), "唯一 %d / 共 %d" % (len(_ids), len(_pl)))
        check("_qq_ep_title 能取到首集标题", bool(video._qq_ep_title(_raw, 0)), video._qq_ep_title(_raw, 0))
        print("    前 3 集: " + " | ".join("%s %s" % (x["episode_number"], x["title"][:16]) for x in _pl[:3]))

# ---------- 8. 弹幕 ----------
head("8. _qq_danmu 弹幕/评论")
if not _pl:
    skip("弹幕列表", "无可用 vid(选集为空)")
else:
    _d = video._qq_danmu(_pl[0]["id"])
    if not _d:
        skip("弹幕列表", "该视频无弹幕或网络失败")
    else:
        check("返回 list[dict]", isinstance(_d, list) and all(isinstance(x, dict) for x in _d), "共 %d 条" % len(_d))
        check("每条含 content / up / time", all({"content", "up", "time"} <= set(x) for x in _d))
        _ups = [x["up"] for x in _d]
        check("按点赞降序", _ups == sorted(_ups, reverse=True))
        print("    热评: " + " | ".join("赞%d %s" % (x["up"], x["content"][:14]) for x in _d[:3]))

# ---------- 汇总 ----------
print("\n" + "=" * 56)
print("被测 vid=%s  cid=%s" % (VID, CID))
print("通过 %d   失败 %d   跳过 %d" % (len(_P), len(_F), len(_S)))
if _F:
    print("失败项: " + " / ".join(_F))
sys.exit(1 if _F else 0)
