# -*- coding: utf-8 -*-
"""界面偏好记忆 —— 记住用户调过的界面参数,下次打开还按这个来。

当前记的:
    player.panel_ratio   播放器右侧"选集/评论"面板的宽度,占窗口宽的比例
                         (拖中间那条分隔条调出来的,界面逻辑见 view/player/panel.py)

存在哪
    程序目录 config/ 下的 uiprefs.json(与 config.json 同目录)。
    单独开一个文件是刻意的:config.json 是人工维护的配置(字段说明收在同一份的 _readme 键里),
    界面偏好是程序自己维护的数据,放这里互不干扰;两者都用 JSON,读写规则也统一。

用法
    get_float("player", "panel_ratio")          # 没有 / 读不了 -> 返回 default(None)
    set_value("player", "panel_ratio", 0.2941)  # 写失败静默忽略:丢个偏好不该影响别的功能

约定:本模块只依赖 model.paths,不 import tkinter / PIL / model.api,任何模块都能安全引它。
"""
from model.paths import _README_UIPREFS, _config_path, _json_load, _json_save

_JSON_NAME = "uiprefs.json"


def path():
    """配置文件路径:程序目录 config/ 下的 uiprefs.json(与 config.json 同目录)"""
    return _config_path(_JSON_NAME)


def _read():
    """读整份偏好 → dict;文件不存在或读不了返回 {}"""
    return _json_load(_JSON_NAME)


def get(section, key, default=None):
    """按"段 + 键"取值;没有这项或读不了就返回 default"""
    _sec = _read().get(section)
    if not isinstance(_sec, dict):
        return default
    _v = _sec.get(key)
    return default if _v is None else _v


def get_float(section, key, default=None):
    """按"段 + 键"取浮点数;没有这项或值不是数字就返回 default"""
    _v = get(section, key, None)
    if _v is None:
        return default
    try:
        return float(str(_v).strip())
    except Exception:
        return default


def set_value(section, key, value):
    """写一项并立刻落盘(值按 JSON 原生类型存:数字就是数字,不强行转字符串);成功 True,失败 False

    先把整份读回来再写,保证 uiprefs.json 里别的键(含 _readme 说明)不会丢。
    """
    try:
        _obj = _read()
        if not isinstance(_obj.get("_readme"), list):
            _obj["_readme"] = list(_README_UIPREFS)
        _sec = _obj.get(section)
        if not isinstance(_sec, dict):
            _sec = {}
            _obj[section] = _sec
        _sec[key] = value
        return _json_save(_JSON_NAME, _obj)
    except Exception:
        return False


__all__ = ["path", "get", "get_float", "set_value"]
