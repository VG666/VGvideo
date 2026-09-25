# -*- coding: utf-8 -*-
"""程序目录 / 平台能力 / 数据文件(基础层,不依赖任何其他 vg* 模块)

职责:
    application_path  打包后指向临时解包目录(_MEIPASS),只放只读资源(videovlc/、ico/logo.ico)
    _run_dir          真正的"程序目录":Recordset 等可写数据都放这里
    IS_WINDOWS/IS_MACOS/IS_LINUX   平台标记
    windll            非 Windows 下为 None
    _data_path        统一取"程序目录"下的路径
    _config_path      统一取配置文件路径(优先 config/ 下的,根部还留着旧文件才认旧的)
    _json_load/_json_save   配置文件的 JSON 读写(统一入口,读不了不抛异常)
    _cfg_section      取 config.json 里某一段(取不到返回空字典)
    _download_dir/_save_download_dir   下载目录的读与写(都走 config.json 的 path.download_dir)
    _download_dir_arg 下载目录拼进播放器命令行的形式(带外层双引号)
    _ini_obj          传统 ini -> 字典(只用于把历史版本的 ini 升级成 JSON)
    _ensure_data_files 保证 config/ 与 Recordset/ 目录存在,并把历史 ini 升级进 JSON(升级后删除)
    _UTIL_DIR         "程序目录/utility":vlc.py / max_win.py / windnd.py / ToolTips.py 的所在地,导入本模块时挂进 sys.path

配置文件布局:配置统一用 JSON,收在"程序目录/config/"里 ——
            config.json   主配置(人工维护:path / vgapi 等段,字段说明收在同一份的 _readme 键里)
            uiprefs.json  界面偏好(程序自己维护)
            历史版本的 config.ini / file.ini / uiprefs.ini 会在启动时自动升级进这两个 JSON 并**删除原文件**
            (不再保留 .bak);其中 file.ini 的下载目录本就与 config.json 的 path.download_dir 同值,
            升级时合并过去,不再单独留一份文件。若配置文件还摊在程序目录根部,
            _ensure_data_files 会先把它搬进 config/ 再升级。

模块布局:VLC 绑定与三个 Tk 小工具(vlc.py / max_win.py / windnd.py / ToolTips.py)收在 utility/ 里,
         但全项目仍按顶层模块导入(import vlc / import max_win …),所以本模块顺手把 utility/ 挂进 sys.path。

约定:本模块只做"算路径 + 探平台",不 import tkinter / PIL / model.api,任何模块都能安全引它;
     唯一副作用是往 sys.path 里加一条 utility/(见 _UTIL_DIR),且只在源码运行时做。
"""
import json
import os
import sys

# ===== 数据/运行目录统一:打包(冻结)后把可写文件放在 exe 旁边;源码运行放在脚本旁边 =====
# application_path 打包时指向临时解包目录(_MEIPASS),只适合放只读资源(videovlc/、ico/logo.ico 等)
# _run_dir 才是真正"程序目录":config/(三个 JSON 配置)、Recordset 等可写数据都放这里,启动后把工作目录也切过来,
# 使源码运行与打包运行的行为完全一致(很多相对路径如 os.getcwd()\Recordset 从此不再依赖启动目录)。
if getattr(sys, 'frozen', False):

    # If the application is run as a bundle, the pyInstaller bootloader

    # extends the sys module by a flag frozen=True and sets the app 
    # path iinto variable _MEIPASS'.

    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    if getattr(sys, 'frozen', False):
        _run_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        _run_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except Exception:
    _run_dir = os.getcwd()


# ===== utility/(VLC 绑定 + Tk 小工具)挂进 sys.path =====
# vlc.py / max_win.py / windnd.py / ToolTips.py 收在 utility/ 里,但全项目都按顶层模块导入(import vlc、import max_win …),
# 它们不带包名,所以路径必须挂上。本模块是最先被导入的基础层,而 main.py 的 `import vlc` 远在其后,放这里最稳妥;
# 打包(frozen)时这些模块已随 import 收进包里,不需要也不能再加这条路径。
_UTIL_DIRNAME = "utility"                              # 工具目录名(程序目录下)
_UTIL_DIR = os.path.join(_run_dir, _UTIL_DIRNAME)       # 程序目录/utility

if not getattr(sys, 'frozen', False):
    try:
        if os.path.isdir(_UTIL_DIR) and _UTIL_DIR not in sys.path:
            sys.path.insert(0, _UTIL_DIR)
    except Exception:
        pass


# ========== 平台标记 ==========
IS_WINDOWS = sys.platform.startswith("win")   # Windows
IS_MACOS = sys.platform == "darwin"            # macOS(Dock图标属应用级自动显示)
IS_LINUX = sys.platform.startswith("linux")    # Linux(X11面板/任务栏)

try:  # 任务栏窗口风格用到的 win32 入口;非 Windows 下为 None
    from ctypes import windll
except Exception:
    windll = None

GWL_EXSTYLE = -20                  # 恢复指令
WS_EX_APPWINDOW = 0x00040000       # 系统变量引导
WS_EX_TOOLWINDOW = 0x00000080      # 系统变量引导


# ========== 配置文件:统一 JSON,收在 config/ ==========
_CFG_DIRNAME = "config"                                   # 配置目录名
_JSON_MAIN = "config.json"                                # 主配置(人工维护:path / vgapi 等段)
_JSON_UIPREFS = "uiprefs.json"                            # 界面偏好(程序自己维护)
_CFG_FILES = (_JSON_MAIN, _JSON_UIPREFS)                  # config/ 下这两个 JSON 就是全部正式配置
_LEGACY_INI = ("config.ini", "file.ini", "uiprefs.ini")   # 历史 ini:启动时升级进 JSON 后删除(一律不留)

# uiprefs.json 的说明文字(迁移时补进去,平时由 model/uiprefs.py 引用,保证只有一份)
_README_UIPREFS = [
    "VG视频 界面偏好(uiprefs.json):程序自己维护 —— 用户拖出来的界面参数记在这里,下次打开按它还原。",
    "手改也能生效(改完重启即可);整份删掉就是恢复默认。",
    "player.panel_ratio:播放器右侧「选集/评论」面板占窗口宽的比例(拖中间那条分隔条调出来的)。",
]
_DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads").replace("\\", "/")


def _data_path(*names):  # 统一取"程序目录"下的路径
    return os.path.join(_run_dir, *names)


def _config_dir():  # 配置目录(config.json / uiprefs.json 都归这里)
    return os.path.join(_run_dir, _CFG_DIRNAME)


def _config_path(name):  # 配置文件路径:优先 config/ 下的;根部还留着历史版本的旧文件就认旧的(不迁)
    _new = os.path.join(_run_dir, _CFG_DIRNAME, name)
    _old = os.path.join(_run_dir, name)
    if os.path.isfile(_new) or not os.path.isfile(_old):
        return _new
    return _old


def _json_load(name, default=None):  # 读 config/ 下的 JSON → dict;文件不存在/读不了/不是对象 → default(缺省 {})
    try:
        with open(_config_path(name), encoding="utf-8-sig") as _f:
            _obj = json.load(_f)
        if isinstance(_obj, dict):
            return _obj
    except Exception:
        pass
    return {} if default is None else default


def _json_save(name, obj):  # 写 config/ 下的 JSON(缩进 2、中文原样);成功 True,失败 False(不抛异常)
    try:
        _p = os.path.join(_config_dir(), name)
        os.makedirs(os.path.dirname(_p), exist_ok=True)
        with open(_p, "w", encoding="utf-8") as _f:
            json.dump(obj, _f, ensure_ascii=False, indent=2)
            _f.write("\n")
        return True
    except Exception:
        return False


def _cfg_section(section):  # 取主配置 config.json 里某一段 → dict(没有这一段就空字典)
    _sec = _json_load(_JSON_MAIN).get(section)
    return _sec if isinstance(_sec, dict) else {}


def _download_dir():  # 下载目录(config.json 的 path.download_dir):返回纯路径,不含引号;没配就用系统"下载"目录
    _v = str(_cfg_section("path").get("download_dir") or "").strip()
    return _v or _DEFAULT_DOWNLOAD_DIR


def _download_dir_arg():  # 下载目录拼进播放器命令行的形式(路径可能带空格,必须补一对双引号)
    return '"' + str(_download_dir()).strip('"').strip("'") + '"'


def _save_download_dir(path):  # 写下载目录到 config.json 的 path.download_dir(整份读回再写,别的键不动)
    _v = str(path or "").strip().strip('"').strip("'")
    if not _v:
        return False
    _obj = _json_load(_JSON_MAIN)
    _sec = _obj.get("path")
    if not isinstance(_sec, dict):
        _sec = {}
        _obj["path"] = _sec
    _sec["download_dir"] = _v
    return _json_save(_JSON_MAIN, _obj)


def _ini_obj(path):  # 传统 ini → {段名: {键: 值}}(段名/键名保持原样,无段的键归到 "" 段);解析不了返回 None
    try:
        _out = {}
        _sec = ""
        with open(path, encoding="utf-8-sig", errors="replace") as _f:
            for _ln in _f:
                _ln = _ln.strip()
                if not _ln or _ln[0] in ";#":
                    continue
                if _ln.startswith("[") and _ln.endswith("]"):
                    _sec = _ln[1:-1].strip()
                    _out.setdefault(_sec, {})
                    continue
                if "=" not in _ln:
                    continue
                _k, _v = _ln.split("=", 1)
                _out.setdefault(_sec, {})[_k.strip()] = _v.strip()
        return _out
    except Exception:
        return None


def _as_number(text):  # 迁移用:能当数字就当数字存(JSON 里写成 0.324 比 "0.324" 干净),否则原样
    _s = str(text).strip()
    try:
        return float(_s)
    except Exception:
        return text


def _upgrade_legacy_ini():  # 历史 ini → JSON:逐项搬运(只补目标里没有的键),搬完删除 ini;幂等,坏文件跳过
    _dir = _config_dir()

    # 1) config.ini → config.json 的 path / vgapi 段
    _p = os.path.join(_dir, "config.ini")
    if os.path.isfile(_p):
        _old = _ini_obj(_p)
        if isinstance(_old, dict):
            _main = _json_load(_JSON_MAIN)
            _added = False
            for _sec, _items in _old.items():
                _name = (_sec or "vgapi").strip().lower() or "vgapi"
                if _name not in ("path", "vgapi"):
                    continue                      # 认不出的段整段丢掉:宁缺勿滥
                _cur = _main.get(_name)
                if not isinstance(_cur, dict):
                    _cur = {}
                    _main[_name] = _cur
                _have = set(str(_k).strip().lower() for _k in _cur)
                for _k, _v in _items.items():
                    if str(_k).strip().lower() in _have:
                        continue                  # config.json 是更新的一版,同名的以它为准
                    _cur[_k.strip()] = _v
                    _added = True
            if _added:
                _json_save(_JSON_MAIN, _main)
        try:
            os.remove(_p)                          # 用户要求:ini 一律不留
            print("配置已升级为 JSON 并删除旧文件: config.ini → config.json")
        except Exception:
            pass

    # 2) file.ini(整份就是一个带引号的目录) → config.json 的 path.download_dir
    _p = os.path.join(_dir, "file.ini")
    if os.path.isfile(_p):
        _v = ""
        try:
            with open(_p, encoding="utf-8", errors="replace") as _f:
                _v = _f.read().strip()
        except Exception:
            _v = ""
        if _v and not str(_cfg_section("path").get("download_dir") or "").strip():
            _save_download_dir(_v)
        try:
            os.remove(_p)
            print("配置已升级为 JSON 并删除旧文件: file.ini → config.json 的 path.download_dir")
        except Exception:
            pass

    # 3) uiprefs.ini → uiprefs.json
    _p = os.path.join(_dir, "uiprefs.ini")
    if os.path.isfile(_p):
        _old = _ini_obj(_p)
        if isinstance(_old, dict):
            _ui = _json_load(_JSON_UIPREFS)
            if not isinstance(_ui.get("_readme"), list):
                _ui["_readme"] = list(_README_UIPREFS)
            _added = False
            for _sec, _items in _old.items():
                _name = (_sec or "player").strip().lower() or "player"
                _cur = _ui.get(_name)
                if not isinstance(_cur, dict):
                    _cur = {}
                    _ui[_name] = _cur
                _have = set(str(_k).strip().lower() for _k in _cur)
                for _k, _v in _items.items():
                    if str(_k).strip().lower() in _have:
                        continue
                    _cur[_k.strip()] = _as_number(_v)
                    _added = True
            if _added:
                _json_save(_JSON_UIPREFS, _ui)
        try:
            os.remove(_p)
            print("配置已升级为 JSON 并删除旧文件: uiprefs.ini → uiprefs.json")
        except Exception:
            pass


def _migrate_config_files():  # 老布局(配置文件摊在程序目录根部)一次性归拢进 config/
    for _n in _CFG_FILES + _LEGACY_INI:
        _old = os.path.join(_run_dir, _n)
        _new = os.path.join(_run_dir, _CFG_DIRNAME, _n)
        if os.path.isfile(_old) and not os.path.exists(_new):
            try:
                os.replace(_old, _new)   # 搬不动(只读盘等)就算了:读取时 _config_path 依然认得旧位置
            except Exception:
                pass


def _ensure_data_files():  # 保证 config/ 与 Recordset/ 目录存在,并把历史 ini 升级进 JSON(升级后删除)
    try:
        os.makedirs(_config_dir(), exist_ok=True)
    except Exception:
        pass
    _migrate_config_files()
    try:
        os.makedirs(_data_path("Recordset"), exist_ok=True)
    except Exception:
        pass
    _upgrade_legacy_ini()


__all__ = [
    "application_path", "_run_dir",
    "IS_WINDOWS", "IS_MACOS", "IS_LINUX", "windll",
    "GWL_EXSTYLE", "WS_EX_APPWINDOW", "WS_EX_TOOLWINDOW",
    "_data_path", "_config_dir", "_config_path",
    "_json_load", "_json_save", "_cfg_section",
    "_download_dir", "_download_dir_arg", "_save_download_dir",
    "_ini_obj", "_migrate_config_files", "_ensure_data_files",
]
