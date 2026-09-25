# -*- coding: utf-8 -*-
"""
取真实播放地址 + 立即播放的独立调试脚本。

取流本体不在客户端:vid → 真实播放地址 一律向数据服务要(config/config.json 的
vgapi.PLAY_API_BASE),本脚本只负责选集、调接口、试播。
接口与 Cookie 全部复用 main.py 那一份(_qq_episodes / _resolve_url),换 Cookie 只改
config/config.json 即可,本脚本自动跟着变,不用维护两套。

前置:数据服务要在线 —— 客户端不再自建服务、也没有本机解析兜底:
      python tx_server/app.py    # 本机跑起数据服务(默认 127.0.0.1:8765,与 PLAY_API_BASE 默认值一致)
      或把 tx_server/ 部署到别处,再把地址填进 config/config.json 的 vgapi.PLAY_API_BASE。

用法示例:
    python test/play.py r0047gdjpw6                                  # 直接播该 vid
    python test/play.py https://v.qq.com/x/cover/xxx/yyyy.html       # 播链接里那一集
    python test/play.py --cid mzc00200xf3rir6 --ep 3                 # 播某剧第 3 集
    python test/play.py --search 仙逆 --ep 1                         # 搜剧名后播第 1 集
    python test/play.py --cid mzc00200xf3rir6 --list                 # 只列选集
    python test/play.py r0047gdjpw6 --url-only                       # 只要真实地址,不播放
    python test/play.py r0047gdjpw6 --json                           # 结构化输出
    python test/play.py r0047gdjpw6 -o url.txt --player none         # 地址存文件

退出码:0 成功 / 1 解析失败(含会员、DRM、网络不可用)
"""
import argparse
import contextlib
import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))   # test/ 目录:search_api.py 就放在这儿
_ROOT = os.path.dirname(HERE)                       # 程序目录(根):main.py 与 videovlc/ 在根上
for _d in (_ROOT, HERE):
    if _d not in sys.path:
        sys.path.insert(0, _d)

for _s in (sys.stdout, sys.stderr):  # Windows 控制台默认 GBK,标题/地址里有中文会炸
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_VID_RE = re.compile(r"^[a-z0-9]{11}$", re.I)  # vid 固定 11 位(如 r0047gdjpw6)


def log(msg=""):
    """提示信息一律走 stderr,保证 --url-only 时 stdout 只有一行纯地址,方便管道"""
    print(msg, file=sys.stderr)


def load_video():
    """导入 main.py 复用其取流实现;导入期间它会把工作目录切走,这里切回来"""
    os.environ.setdefault("PYTHON_VLC_MODULE_PATH", os.path.join(_ROOT, "videovlc"))
    cwd = os.getcwd()
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):  # main.py 模块级有一句 print(application_path),屏蔽掉
            import main as video    # 程序入口已改名 main.py;本脚本沿用 video 这个别名(video.xxx 都指它)
    finally:
        try:
            os.chdir(cwd)
        except Exception:
            pass
    return video


def parse_target(s):
    """从 vid 或播放页链接里抽出 (cid, vid);链接形如 /x/cover/<cid>/<vid>.html"""
    s = (s or "").strip()
    if not s:
        return "", ""
    if not s.lower().startswith(("http://", "https://")):
        return "", (s if _VID_RE.match(s) else _VID_RE.search(s).group(0) if _VID_RE.search(s) else s)
    cid = ""
    m = re.search(r"/cover/([a-z0-9]{11})", s, re.I)  # 剧集页:/x/cover/<cid>.html
    if m:
        cid = m.group(1)
    vid = ""
    for pat in (r"/page/([a-z0-9]{11})",  # 单视频页:/x/page/<vid>.html
                r"[?&]vid=([a-z0-9]{11})",  # 带 ?vid= 的选集页
                r"/([a-z0-9]{11})\.html"):  # 剧集页里那一集:/x/cover/<cid>/<vid>.html
        m = re.search(pat, s, re.I)
        if m and m.group(1) != cid:
            vid = m.group(1)
            break
    return cid, vid


def list_episodes(video, cid):
    """取该 cid 的选集,返回 [(vid, 显示名), ...]"""
    txt = video._qq_episodes(cid)
    if not txt:
        return []
    pl = ((video._json_load(txt).get("PlaylistItem") or {}).get("videoPlayList")) or []
    return [(str(x.get("id") or ""), str(x.get("title") or x.get("episode_number") or "")) for x in pl if x.get("id")]


def pick_episode(video, cid, ep):
    """取第 ep 集(1 起,越界自动夹到首/末集),返回 (vid, 显示名)"""
    eps = list_episodes(video, cid)
    if not eps:
        return "", ""
    i = max(1, min(int(ep or 1), len(eps))) - 1
    if i != int(ep or 1) - 1:
        log("[提示] 该剧共 %d 集,已自动选第 %d 集" % (len(eps), i + 1))
    return eps[i]


def find_by_name(name):
    """按剧名搜索,返回 (kind, id, 标题);kind 为 cid(剧集) / vid(单条)"""
    try:
        import search_api
    except Exception as e:
        return "", "", "搜索模块不可用: %s" % e
    try:
        r = search_api.search(name)
    except Exception as e:
        return "", "", "搜索失败: %s" % e
    items = r.get("items") or []
    if not items:
        return "", "", "没有搜到「%s」" % name
    cover = next((x for x in items if x.get("kind") == "cover"), None)  # 优先剧集,才能继续选集
    it = cover or items[0]
    return ("cid" if cover else "vid"), str(it.get("id") or ""), str(it.get("title") or "")


def ensure_api(video):
    """确认数据服务在线:客户端不再自建服务,这里只探活并说清楚怎么把它跑起来"""
    try:
        ok, why = video.play_api_health()
    except Exception as e:
        ok, why = False, "健康检查异常: %s" % e
    log("[服务] %s" % (("数据服务在线: " + why) if ok else ("数据服务不可用: " + why)))
    if not ok:
        log("[提示] 请先跑起数据服务: python tx_server/app.py")
        log("       (或把 tx_server/ 部署到别的机器,再把地址填进 config/config.json 的 vgapi.PLAY_API_BASE)")
        log("       当前数据源: %s" % (video.play_api_base() or "(未配置)"))
    return ok


def _kind_of(url):
    """按地址形态猜类型(只用于打印;真正的 HLS→MP4 兜底在服务端)"""
    _u = str(url or "").lower()
    if ".m3u8" in _u:
        return "HLS(m3u8)"
    if ".mp4" in _u:
        return "MP4"
    return "网络接口"


def real_url(video, vid):
    """取真实地址:客户端只有这一条路 —— 调数据服务;返回 (地址, 类型)"""
    try:
        u = str(video._resolve_url(vid) or "").strip()
    except Exception:
        u = ""
    if u.startswith("http"):
        return u, _kind_of(u)
    return "", ""


def play_with_vlc(video, url, title):
    """用项目自带的 libvlc(videovlc/) 播放;失败返回 False 由调用方回退"""
    if getattr(video, "vlc", None) is None:
        return False
    try:
        vlc = video.vlc
        inst = vlc.Instance("--quiet", "--no-video-title-show", "--network-caching=3000")
        if not inst:
            return False
        p = inst.media_player_new()
        m = inst.media_new(url)
        try:
            m.set_meta(vlc.Meta.Title, title or "Video")
        except Exception:
            pass
        p.set_media(m)
        p.play()
        time.sleep(1.5)
        if p.get_state() == vlc.State.Error:
            log("[失败] VLC 起播失败")
            return False
        log("[播放中] %s" % (title or url))
        log("        窗口已弹出,按 Ctrl+C 停止")
        end = (vlc.State.Ended, vlc.State.Error, vlc.State.Stopped)
        while p.get_state() not in end:
            time.sleep(0.5)
        p.stop()
        p.release()
        return True
    except KeyboardInterrupt:
        log("\n[已停止]")
        return True
    except Exception as e:
        log("[失败] VLC 播放异常: %s" % e)
        return False


def play_with_system(url):
    """交给系统默认播放器/关联程序"""
    try:
        os.startfile(url)  # noqa: 仅 Windows
        log("[已交给系统默认程序] %s" % url[:90])
        return True
    except Exception as e:
        log("[失败] 调起系统播放器失败: %s" % e)
        return False


def main():
    ap = argparse.ArgumentParser(
        description="腾讯视频:取真实播放地址并播放(复用 main.py 的接口与 Cookie)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("target", nargs="?", help="vid 或腾讯视频链接")
    ap.add_argument("--cid", help="剧集 cid(配合 --ep 选集)")
    ap.add_argument("--ep", type=int, default=1, help="第几集,从 1 开始(默认 1)")
    ap.add_argument("--search", metavar="剧名", help="按剧名搜索后再解析")
    ap.add_argument("--list", action="store_true", help="只列出选集,不解析不播放")
    ap.add_argument("--defn", default="", choices=["", "fhd", "shd", "hd", "sd"],
                    help="清晰度;已随取流下沉服务端,这里只保留兼容旧命令(传了会提示不生效)")
    ap.add_argument("--url-only", action="store_true", help="只把真实地址打到 stdout,不播放")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    ap.add_argument("-o", "--out", metavar="文件", help="把真实地址写入文件")
    ap.add_argument("--player", default="vlc", choices=["vlc", "system", "none"],
                    help="vlc=内置播放(默认) / system=系统默认程序 / none=不播放")
    args = ap.parse_args()

    if args.defn:
        log("[提示] --defn 已不生效:清晰度策略在服务端(tx_server/vgplay,PLAY_BACKENDS)")

    cid, vid, name = args.cid or "", "", ""
    if args.search:
        kind, sid, name = find_by_name(args.search)
        if not sid:
            log("[失败] %s" % name)
            return 1
        cid, vid = (sid, "") if kind == "cid" else ("", sid)
        log("[搜索] %s -> %s %s" % (args.search, kind, sid))
    elif args.target:
        cid, vid = parse_target(args.target)
        if not cid and not vid:
            log("[失败] 认不出这个 vid / 链接: %s" % args.target)
            return 1
    if not cid and not vid:
        ap.print_help()
        return 1

    video = load_video()

    if cid and args.list:  # 只列选集
        eps = list_episodes(video, cid)
        if not eps:
            log("[失败] 取不到选集(cid 可能失效)")
            return 1
        log("共 %d 集:" % len(eps))
        for i, (v, t) in enumerate(eps, 1):
            print("%3d\t%s\t%s" % (i, v, t))
        return 0

    if cid and not vid:  # 只给了剧集:按 --ep 选一集
        vid, name = pick_episode(video, cid, args.ep)
        if not vid:
            log("[失败] 取不到第 %d 集(cid 可能失效或该剧暂无选集)" % args.ep)
            return 1

    if not ensure_api(video):
        log("[失败] 数据服务不可用:先跑起 tx_server/app.py,或把服务地址填进 config/config.json 的 vgapi.PLAY_API_BASE")
        return 1

    log("[解析] vid=%s %s" % (vid, ("/ " + name) if name else ""))
    url, kind = real_url(video, vid)
    if not url:
        log("[失败] 没取到可用地址:该集可能是会员/DRM 内容,或服务端 Cookie 已过期(失败原因见服务端输出)")
        return 1
    log("[成功] %s 地址" % kind)

    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(url)
            log("[已保存] %s" % os.path.abspath(args.out))
        except Exception as e:
            log("[失败] 写文件失败: %s" % e)

    if args.json:
        print(json.dumps({"vid": vid, "cid": cid, "title": name, "kind": kind, "url": url},
                         ensure_ascii=False, indent=2))
    elif args.url_only:
        print(url)  # stdout 只这一行,便于 for /f、管道、xargs 取用
    else:
        log("地址: %s" % url)

    if args.url_only or args.player == "none":
        return 0
    if args.player == "system":
        return 0 if play_with_system(url) else 1
    if not play_with_vlc(video, url, name):  # VLC 起不来时回退系统播放器
        log("[回退] 改用系统默认程序")
        return 0 if play_with_system(url) else 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
