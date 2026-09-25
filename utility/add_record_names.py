# -*- coding: utf-8 -*-
"""观看记录补剧名 + 升级成 JSON(Recordset/<剧集id>.json)

做两件事:
    1. 格式升级:上一代 <剧集id>.ini(传统 ini)与更老的 <剧集id>.vgini(只有两行:集数 / 进度)
       统一改写成本文件同款的 JSON —— 记事本能直接看懂、能手改,别的工具也好读;
    2. 补名字:记录里 name 还是空的,联网按剧集id查出剧名补进去(查不到就留空,下次再跑继续补)。

JSON 长这样(键名与 model/records.py 的 _rec_read/_rec_save 完全一致):

    {
      "cid": "mzc00200js3mdvw",
      "name": "斗罗大陆Ⅱ绝世唐门",
      "episode": 3,
      "progress": 0.2880264222621918,
      "update": "2026-09-11 03:44:26"
    }

用法(在程序目录里执行;直接 python 本脚本也行,程序目录默认取本脚本的上一级):
    python utility/add_record_names.py                      # 升级格式 + 补剧名(会改写 Recordset 里的记录)
    python utility/add_record_names.py --dry-run            # 只看结果,不动任何文件
    python utility/add_record_names.py --no-net             # 只升级格式,不联网查剧名
    python utility/add_record_names.py --dir "D:\\VG视频"      # 指定别的程序目录

说明:
    * 改写时会保留文件原有的修改时间,历史记录页"最近观看"的顺序不会被打乱;
    * 同一部剧同时留着 .ini / .vgini 时,写完 .json 会把旧格式文件全部删掉,免得历史页出现两条;
    * 联网部分复用 model.api 接口层,自动带上程序目录 config/config.json 里的 QQ_COOKIE 等配置。
"""
import argparse
import json
import os
import re
import sys
import time

# 程序目录(默认):本脚本收在 utility/ 里,程序目录是它的上一级 —— config/ 与 Recordset 都在那儿
_RUN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REC_DIR = "Recordset"                                  # 记录目录
_EXT = ".json"                                          # 现用后缀:JSON
_OLD_EXTS = (".ini", ".vgini")                          # 历史后缀:只读兼容,写完即删

# 片名结尾的集数/花絮标记:"斗罗大陆Ⅱ绝世唐门 第001话" -> "斗罗大陆Ⅱ绝世唐门"
_RE_BRACKET = re.compile(r"\s*[（(](?:预告|片花|花絮|MV|mv|彩蛋|特辑|番外|片段|主题曲|片尾曲|插曲)[^（()）]{0,10}[)）]\s*$")
_RE_EP = re.compile(r"[\s·\-—_]*(?:第\s*)?[0-9０-９零一二三四五六七八九十百千]{1,6}\s*[集话期章篇部回季](?:\s*[（(][^（()）]{0,10}[)）])?\s*$")


def _strip_ep(t):
    """把"剧名 第001话"这类片名还原成剧名(去掉结尾的集数标记;去完为空就退回原样)"""
    _t = str(t or "").strip()
    if not _t:
        return ""
    _p = _RE_EP.sub("", _RE_BRACKET.sub("", _t).strip()).strip()
    return _p or _t


def _read_rec(path):
    """读记录 → {"cid","name","episode","progress","_json"};支持 JSON 与两代历史格式,读不出返回 None"""
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as _f:
            _txt = _f.read()
    except Exception:
        return None
    _r = {"cid": "", "name": "", "episode": 0, "progress": 0.0, "_json": False}
    if str(path).lower().endswith(_EXT):            # 现用格式:JSON
        try:
            _j = json.loads(_txt)
        except Exception:
            return None
        if not isinstance(_j, dict):
            return None
        _r["_json"] = True
        _r["cid"] = str(_j.get("cid") or "").strip()
        _r["name"] = str(_j.get("name") or "").strip()
        try: _r["episode"] = max(0, int(float(_j.get("episode") or 0)))
        except Exception: pass
        try: _r["progress"] = max(0.0, min(1.0, float(_j.get("progress") or 0.0)))
        except Exception: pass
        return _r
    if "[" in _txt:                      # 上一代传统 ini:逐行"键 = 值",段名不参与判断,键名不分大小写
        for _ln in _txt.replace("\r", "").split("\n"):
            _ln = _ln.strip()
            if not _ln or _ln[0] in ";#" or "=" not in _ln:
                continue
            _k, _v = _ln.split("=", 1)
            _k, _v = _k.strip().lower(), _v.strip()
            if _k == "cid":
                _r["cid"] = _v
            elif _k == "name":
                _r["name"] = _v
            elif _k in ("episode", "ep", "index"):
                try: _r["episode"] = max(0, int(float(_v)))
                except Exception: pass
            elif _k in ("progress", "position", "pos"):
                try: _r["progress"] = max(0.0, min(1.0, float(_v)))
                except Exception: pass
        return _r
    _ls = _txt.replace("\r", "").split("\n")   # 更老格式:第1行集数,第2行进度
    try:
        if _ls[0].strip():
            _r["episode"] = max(0, int(float(_ls[0])))
    except Exception:
        pass
    try:
        if len(_ls) > 1 and _ls[1].strip():
            _r["progress"] = max(0.0, min(1.0, float(_ls[1])))
    except Exception:
        pass
    return _r


def _write_rec(path, cid, name, episode, progress, mtime):
    """按 JSON 写回记录,并把修改时间还原成 mtime(历史页排序不变)"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _obj = {"cid": str(cid), "name": str(name), "episode": int(episode),
            "progress": float(progress),
            "update": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))}
    with open(path, "w", encoding="utf-8") as _f:
        json.dump(_obj, _f, ensure_ascii=False, indent=2)
        _f.write("\n")
    if mtime:
        try: os.utime(path, (mtime, mtime))
        except Exception: pass


def _cid_of(name):
    """文件名 → 剧集id:认 .json / .ini / .vgini 三种后缀,不是记录文件返回空串"""
    _low = name.lower()
    if _low.endswith(_EXT):
        return name[:-len(_EXT)]
    for _ext in (".vgini", ".ini"):     # .vgini 在前:.ini 是它的后缀,别被截错
        if _low.endswith(_ext):
            return name[:-len(_ext)]
    return ""


def _scan(rec_abs):
    """扫描记录目录 → [(cid, 原文件路径, 记录内容)],同一部剧只留一条(现用 .json 优先)"""
    try:
        _names = os.listdir(rec_abs)
    except Exception as _e:
        print("打不开记录目录:", rec_abs, _e)
        return []
    _out, _done = [], set()
    _rank = {_EXT: 0, ".ini": 1, ".vgini": 2}
    for _n in sorted(_names, key=lambda _s: _rank.get(("." + _s.rsplit(".", 1)[-1].lower()), 9)):
        _cid = _cid_of(_n)
        if not _cid or _cid in _done:
            continue
        _done.add(_cid)
        _p = os.path.join(rec_abs, _n)
        _r = _read_rec(_p)
        if _r is None:
            print("跳过(读不了):", _p)
            continue
        _out.append((_cid, _p, _r))
    return _out


def _query_name(episodes, cid, ep=0):
    """按剧集id查剧名 → (剧名, 来源);查不到返回 ("", "")"""
    try:
        _js = episodes(cid)
    except Exception:
        return "", ""
    if not _js:
        return "", ""
    try:
        _j = json.loads(_js)
    except Exception:
        return "", ""
    _pl = (_j.get("PlaylistItem") or {})
    _t = str(_pl.get("title") or "").strip()
    if _t and _t != str(cid):                       # 接口拿不到专辑名时会用 cid 顶替,这种不算查到
        return _t, "专辑名"
    _list = _pl.get("videoPlayList") or []
    if _list:
        _i = min(max(0, int(ep)), len(_list) - 1)
        _t = _strip_ep(str(_list[_i].get("title") or "") or str(_list[_i].get("episode_number") or ""))
        if _t and _t != str(cid):
            return _t, "选集片名"
    return "", ""


def main():
    _ap = argparse.ArgumentParser(description="观看记录补剧名 + 升级成 JSON")
    _ap.add_argument("--dir", default=_RUN_DIR, help="程序目录(默认取本脚本的上一级)")
    _ap.add_argument("--no-net", action="store_true", help="不联网,只做格式升级")
    _ap.add_argument("--dry-run", action="store_true", help="只打印结果,不改动任何文件")
    _ap.add_argument("--delay", type=float, default=0.2, help="每次联网查询后的间隔秒数(默认 0.2)")
    _a = _ap.parse_args()

    _run = os.path.abspath(_a.dir)
    _rec_abs = os.path.join(_run, _REC_DIR)
    print("程序目录:", _run)
    print("记录目录:", _rec_abs)
    if not os.path.isdir(_rec_abs):
        print("没有记录目录:先运行一次主程序,它会自动建出来。")
        return 1

    _episodes = None
    if not _a.no_net:
        sys.path.insert(0, _run)                    # 让脚本能用程序目录里的 model.api 包
        try:
            from model.api import _qq_episodes, configure
            configure(run_dir=_run)                 # 让接口层读到程序目录 config/config.json(Cookie 等)
            _episodes = _qq_episodes
        except Exception as _e:
            print("接口层导入失败,这次只升级格式(等同于 --no-net):", _e)

    _rows = _scan(_rec_abs)
    print("发现 %d 部剧的观看记录%s\n" % (len(_rows), "(只看看不动文件)" if _a.dry_run else ""))
    _n_fmt = _n_name = _n_fail = _n_skip = 0
    _left = []
    for _cid, _p, _r in _rows:
        _old_name = str(_r.get("name") or "").strip()
        _ep = max(0, int(_r.get("episode") or 0))
        _pos = max(0.0, min(1.0, float(_r.get("progress") or 0.0)))
        try:
            _mtime = os.path.getmtime(_p) or time.time()
        except Exception:
            _mtime = time.time()
        _name, _src = _old_name, ("已有" if _old_name else "")
        if not _name and _episodes is not None:     # 没名字:联网查
            _name, _src = _query_name(_episodes, _cid, _ep)
            time.sleep(max(0.0, _a.delay))
        if not _name:
            _n_fail += 1
            _left.append(_cid)
        elif not _old_name:
            _n_name += 1
        if not _r.get("_json"):
            _n_fmt += 1
        _need = (not _r.get("_json")) or (_ep != int(_r.get("episode") or 0)) or (_pos != float(_r.get("progress") or 0.0)) or (_name != _old_name)
        _new_path = os.path.join(_rec_abs, _cid + _EXT)
        _tag = "不动"
        if not _need:
            _n_skip += 1
        elif _a.dry_run:
            _tag = "待改"
        else:
            _tag = "升级" if not _r.get("_json") else ("补名" if _name and not _old_name else "整理")
            try:
                _write_rec(_new_path, _cid, _name, _ep, _pos, _mtime)
            except Exception as _e:
                print("  写入失败:", _new_path, _e)
                continue
            for _oe in _OLD_EXTS:                   # 历史格式已升级成 JSON,删掉免得历史页出现两条
                _op = os.path.join(_rec_abs, _cid + _oe)
                if os.path.isfile(_op):
                    try: os.remove(_op)
                    except Exception as _e: print("  删除旧记录失败:", _op, _e)
        print("  %-4s %-24s %-24s 第%d集 已看%d%%  [%s]" % (_tag, _cid, _name or "-- 没查到 --", _ep + 1, int(round(_pos * 100)), _src or "-"))
    print("\n合计:%d 条,其中升级格式 %d 条、补到剧名 %d 条、无需改动 %d 条、没查到剧名 %d 条" % (len(_rows), _n_fmt, _n_name, _n_skip, _n_fail))
    if _left:
        print("没查到剧名的剧集id:", ", ".join(_left))
        print("这些可以直接用记事本打开 Recordset\\<剧集id>.json,把 name 后面手填上(下次跑本脚本会跳过已有名字的记录)。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
