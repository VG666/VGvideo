# -*- coding: utf-8 -*-
"""观看记录(Recordset/<剧集id>.json)—— 一个大类单独成模块

一个文件一条记录,JSON 格式,记事本能直接看懂/手改。键名请勿改,程序按它们读写:
    {
      "cid": "mzc00200js3mdvw",          # 剧集id(与文件名一致)
      "name": "斗罗大陆Ⅱ绝世唐门",        # 剧名(历史记录页显示;没查到就先留空)
      "episode": 3,                      # 看到第几集(从 0 开始,0=第1集)
      "progress": 0.288026422262,        # 该集播放进度(0~1)
      "update": "2026-09-11 03:44:26"    # 最后观看时间
    }

兼容:历史格式 <剧集id>.ini(传统 ini)与更老的 <剧集id>.vgini(只有两行:集数 / 进度)都还能读;
      模块导入时会把它们一次性升级成 .json 并删除原文件(见 _rec_upgrade_all),
      之后被程序或 add_record_names.py 保存时也走同一套升级逻辑。
"""
import os
from json import dump, loads
from time import strftime, localtime

from model.paths import _data_path

# 记录目录(程序目录下)
_REC_DIR = "Recordset"        # 记录目录
_REC_EXT = ".json"            # 记录文件后缀(JSON,现用)
_REC_OLD_EXT = ".ini"         # 上一代后缀(传统 ini,只读兼容,升级后删除)
_REC_LEGACY_EXT = ".vgini"    # 更老的后缀(两行文本,只读兼容,升级后删除)
_REC_EXTS = (_REC_EXT, _REC_OLD_EXT, _REC_LEGACY_EXT)   # 查找顺序:新的优先

# 主程序启动时注入:取"当前打开中的播放器实例"(main.py 里把 _active_app_player 包一层传进来)。
# 用它而不是直接读主程序的全局,是为了让本模块能独立存在、不反向依赖主程序。
get_active_player = None


def _rec_path(mid):  # 记录文件路径:优先新的 .json,没有再依次退回历史的 .ini / .vgini
    _names = [str(mid) + _ext for _ext in _REC_EXTS]
    for _n in _names:
        _p = _data_path(_REC_DIR, _n)
        if os.path.isfile(_p):
            return _p
    return _data_path(_REC_DIR, _names[0])


def _rec_read(mid):  # 读记录 → {"name","episode","progress","update"};没有记录返回 None
    _p = _rec_path(mid)
    try:
        with open(_p, encoding="utf-8-sig", errors="replace") as _f:
            _txt = _f.read()
    except Exception:
        return None
    if _p.lower().endswith(_REC_EXT):  # 现用格式:JSON
        try:
            _j = loads(_txt)
        except Exception:
            return None
        if not isinstance(_j, dict):
            return None
        _r = {"name": "", "episode": 0, "progress": 0.0, "update": ""}
        _r["name"] = str(_j.get("name") or "").strip()
        _r["update"] = str(_j.get("update") or "").strip()
        try:
            _r["episode"] = max(0, int(float(_j.get("episode") or 0)))
        except Exception:
            pass
        try:
            _r["progress"] = max(0.0, min(1.0, float(_j.get("progress") or 0.0)))
        except Exception:
            pass
        return _r
    _r = {"name": "", "episode": 0, "progress": 0.0, "update": ""}
    if "[" in _txt:  # 历史传统 ini:逐行取"键 = 值";段名不参与判断,键名不分大小写,值里的 = 与 ; 都只算值的一部分
        for _ln in _txt.replace("\r", "").split("\n"):
            _ln = _ln.strip()
            if not _ln or _ln[0] in ";#" or "=" not in _ln:
                continue
            _k, _v = _ln.split("=", 1)
            _k = _k.strip().lower()
            _v = _v.strip()
            if _k == "name":
                _r["name"] = _v
            elif _k == "update":
                _r["update"] = _v
            elif _k in ("cid", "episode", "ep", "index", "vgi"):
                if _k != "cid":
                    try: _r["episode"] = max(0, int(float(_v)))
                    except Exception: pass
            elif _k in ("progress", "position", "pos"):
                try: _r["progress"] = max(0.0, min(1.0, float(_v)))
                except Exception: pass
        return _r
    _ls = _txt.replace("\r", "").split("\n")  # 更老格式:第1行集数,第2行进度(也可能只有一行)
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


def _rec_save(mid, episode=None, progress=None, name=None, update=None):  # 写回记录(永远写 JSON):只覆盖传进来的字段,其余保持原值
    try:
        _old = _rec_read(mid) or {}
        _ep = max(0, int(_old.get("episode") or 0)) if episode is None else max(0, int(episode))
        _po = max(0.0, min(1.0, float(_old.get("progress") or 0.0))) if progress is None else max(0.0, min(1.0, float(progress)))
        _nm = str(_old.get("name") or "") if not str(name or "").strip() else str(name).strip()  # 剧名取不到时保留原值,免得把已有的名字抹掉
        _up = str(update) if str(update or "").strip() else strftime("%Y-%m-%d %H:%M:%S", localtime())  # 迁移时传入原时间,平时取当前
        _obj = {"cid": str(mid), "name": _nm, "episode": _ep, "progress": _po, "update": _up}
        _p = _data_path(_REC_DIR, str(mid) + _REC_EXT)
        try: os.makedirs(os.path.dirname(_p), exist_ok=True)
        except Exception: pass
        with open(_p, "w", encoding="utf-8") as _f:
            dump(_obj, _f, ensure_ascii=False, indent=2)   # indent 保整齐;浮点按最短往返精度写,续播位置不会越读越歪
            _f.write("\n")
        for _ext in (_REC_OLD_EXT, _REC_LEGACY_EXT):   # 历史格式已升级成 JSON,删掉免得历史页出现两条
            _op = _data_path(_REC_DIR, str(mid) + _ext)
            if os.path.isfile(_op):
                try: os.remove(_op)
                except Exception: pass
        return True
    except Exception as _e:
        print("观看记录写入失败:", _e)
        return False


def _rec_upgrade_all():  # 把记录目录里历史格式(.ini / .vgini)的记录一次性升级成 JSON 并删除原文件;幂等,坏文件跳过
    try:
        _dir = _data_path(_REC_DIR)
        for _n in os.listdir(_dir):
            _low = _n.lower()
            if _low.endswith(_REC_EXT):
                continue
            for _ext in (_REC_OLD_EXT, _REC_LEGACY_EXT):
                if _low.endswith(_ext):
                    _mid = _n[:-len(_ext)]
                    if _mid:
                        _src = os.path.join(_dir, _n)
                        _old = _rec_read(_mid) or {}
                        try: _mt = os.path.getmtime(_src)
                        except Exception: _mt = 0.0
                        _up = _old.get("update") or (strftime("%Y-%m-%d %H:%M:%S", localtime(_mt)) if _mt else "")
                        _rec_save(_mid, update=_up)   # 内部先按历史格式读出来、再写成 JSON,并删掉原文件
                        if _mt:                       # 保住原修改时间:历史页按它排序,升级不能把顺序打乱
                            try: os.utime(_data_path(_REC_DIR, str(_mid) + _REC_EXT), (_mt, _mt))
                            except Exception: pass
                    break
    except Exception:
        pass


def _rec_album_name(player=None):  # 剧名:直接取已拿到的剧集信息里的专辑名(PlaylistItem.title);取不到返回空串
    try:
        _p = player
        if not _p and get_active_player is not None:
            try: _p = get_active_player()
            except Exception: _p = None
        _t = getattr(_p, "html", "") or ""
        if _t:
            _j = loads(_t[13:-1] if _t.startswith("QZOutputJson") else _t)
            return str(((_j.get("PlaylistItem") or {}).get("title")) or "").strip()
    except Exception:
        pass
    return ""


_rec_upgrade_all()   # 导入即迁移一次(幂等):历史 ini 记录一律升级成 JSON,不再留旧格式


__all__ = ["_REC_DIR", "_REC_EXT", "_REC_OLD_EXT", "_REC_LEGACY_EXT", "_REC_EXTS",
           "_rec_path", "_rec_read", "_rec_save", "_rec_album_name", "_rec_upgrade_all",
           "get_active_player"]
