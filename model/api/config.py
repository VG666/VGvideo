# -*- coding: utf-8 -*-
"""接口层配置(model.api.config)

程序里所有可调参数集中在这里,主程序不出现这些常量。config.json 的 vgapi 段里其实住着**两拨人**,
分清这一点后面就不容易看混:

    [客户端读] 只有 4 项 —— PLAY_API_BASE / PLAY_API_TOKEN / PLAY_API_TIMEOUT / PLAY_API_CACHE,
               即"怎么连上数据服务"。客户端自己不出网,连上数据服务就什么都有。
    [服务端读] 其余全部(QQ_* / API_BASE / PLAY_BACKENDS / LIVE_M3U …),是"数据源参数":
               由数据源项目的 config 读取,它会把本文件的 vgapi 段**继承**过去 ——
               所以换 Cookie / 换聚合站仍然只改这一个文件,本机跑数据源项目时立刻生效。
               (服务端部署在别的机器上时,把这些项写进那台机器的数据源项目 config.json 即可。)

配置来源(优先级从高到低):
    1) 主程序运行时注入(configure(run_dir=...) / configure(QQ_COOKIE=...));
    2) 程序目录 config/ 下的 config.json —— 启动时自动读取,覆盖下面的同名默认值;
    3) 本文件底部的内置默认值(配置缺失或没写某一项时兜底)。
下载目录(原来单独一份 file.ini)与 vgapi 这批参数同住 config.json,只是分在 path 与 vgapi 两段里,
见本文件末尾的 download_dir()。
布局:config.json 收在"程序目录/config/"里(与 model/paths.py 同一约定);
     根部若还留着历史版本的旧文件,cfg_path() 也会认(见下方)。
历史版本的 config.ini 由 model/paths._ensure_data_files 在启动时升级成 JSON 并删除。
"""
import json
import os
import sys

# ---------------------------------------------------------------------------
# 运行目录:config/config.json、Recordset/ 等所在的"程序目录"
#   主程序启动时会用 configure(run_dir=...) 注入;没注入就按本文件位置回推:
#   video/model/api/config.py -> video/
# ---------------------------------------------------------------------------
_RUN_DIR = ""


def _guess_run_dir():
    try:
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except Exception:
        return os.getcwd()


def run_dir():
    """接口层认为的"程序目录"(打包/源码运行都能对上)"""
    return _RUN_DIR or _guess_run_dir()


def main_argv():
    """运行入口的命令行参数(等价主程序里那个 argv)

    主程序在启动时会重写自己的 argv(如 ["video.exe",1,vid]),所以这里每次现取,
    保证和运行入口看到的完全一致;没有就退回 sys.argv。
    """
    _m = sys.modules.get("__main__")
    _a = getattr(_m, "argv", None)
    return _a if isinstance(_a, (list, tuple)) else sys.argv


def configure(**kw):
    """由主程序注入配置(键名和下面的模块变量一致);run_dir 单独处理

    注入 run_dir 后会按新的程序目录重读一次 config.json —— 打包运行时程序目录
    是 exe 所在目录,不是本文件位置,必须以主程序注入的为准。
    """
    _need_reload = False
    for _k, _v in kw.items():
        if _k == "run_dir":
            globals()["_RUN_DIR"] = str(_v or "")
            _need_reload = True
        else:
            globals()[_k] = _v
    if _need_reload:
        _load_json()
    return True


def get(name, default=None):
    """按名字读配置(调试用)"""
    return globals().get(name, default)


# ---------------------------------------------------------------------------
# 以下为默认值。启动时会用程序目录 config/config.json 里 vgapi 段的同名值覆盖(见文件末尾的
# _load_json),配置里没写的项就沿用下面的值,所以这里保留一份可直接运行的完整默认值。
# 其中只有 PLAY_API_* 那几项是客户端真正读的,其余都是留给服务端继承的"数据源参数"。
# ---------------------------------------------------------------------------

# 外部"聚合解析"站域名(如 "http://xxx.com/");留空则用内置兜底地址。
# 【服务端参数】客户端不读它,只由数据源项目的 "aggregate" 兜底后端使用。
API_BASE = ""

# ---------------- 数据源登录凭据(换号 / 更新登录状态只改这里) ----------------
# 【服务端参数】客户端不读它 —— 下面这一整批都只在服务端出网时用到。
# 用途:数据源项目的请求层对对应域名会自动带上,
#       取流 / 选集 / 弹幕 / 标题 全靠它。
# 说明:留空("")也能解析(接口对匿名请求较宽松),填上可提升清晰度与会员内容成功率。
# 失效表现:播放地址 403、或清晰度只剩 480P —— 重新登录数据源站点复制新 Cookie 覆盖即可。
# 当前值:从数据源站点网页端登录态导出(cookie.txt),PC 网页版完整字段(v_t_* / v_v* 系列)。
QQ_COOKIE = ""
QQ_UA_PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
QQ_UA_MB = ("Mozilla/5.0 (Linux; Android 10; Redmi K30) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/78.0.3904.96 Mobile Safari/537.36")   # 移动端 UA:服务端取流与弹幕接口会读

# ---------------- cKey 签名 / 播放器接口取流(全部在服务端) ----------------
# 用到这批量的是"真正取流"那一处:服务端(算签名、走 vinfo),
# 客户端完全不碰它们,只是让本机跑的数据源项目能继承同一份配置。
# 所以「换 Cookie / 换 guid / 关 vinfo」只改这里一处即可,数据服务那边立刻跟着变。
QQ_GUID = ""              # 个性化 guid(填上成功率更高,32 位十六进制串,从浏览器 Cookie 里取);留空也能用
QQ_USE_VINFO = True       # 关掉即整体退回旧的 getinfo 接口
QQ_VINFO_REFERER = "https://v.qq.com/x/cover/mzc00200w9qrf4g.html"   # 签名算法里用到的占位页地址

# 登录态自动续期(对应 TXSP.py 的 auth_refresh):两个都留空则跳过续期,不影响正常解析。
# 这两个值是数据源登录 SDK 里写死的"网页端固定值",与账号无关,换号也不用改。
# 注意:别再抄浏览器里别的接口(例如 pbaccess 的 GetExtraInfo)的 vappid/vsecret —— 每个接口一
#      套,抄错了续期会直接 401(错误码 35014)。下面这对就是 /user/auth_login 与 /user/auth_refresh 用的。
# 填上后:QQ_COOKIE 里的登录态过期时,服务端会自动换回一条新 Cookie(默认把结果落盘接管,
#         落盘位置见下面的 QQ_COOKIE_CACHE)。
QQ_VAPPID = ""
QQ_VSECRET = ""

# 把 https 流地址降级成 http:本机 VLC 连数据源 CDN 的 https 会不停报
# "main tls client error",结果一直停在 Opening;同 CDN 同路径换 http 就能拉流。
# 【服务端参数】降级在"服务端交付地址时"做,客户端不读它。
QQ_STREAM_HTTP = True

# 【服务端参数】登录态续期换到的 Cookie 是否落盘接管:落盘位置 = 程序目录 config/.cookie_cache.json,
# 删掉即回到上面的 QQ_COOKIE;false = 只在内存里用,不写文件。(数据源项目在本机跑时用同一个路径。)
QQ_COOKIE_CACHE = True
# 【服务端参数】取流后端顺序(逗号分隔):vinfo = 播放器接口 / getinfo = 旧接口 / aggregate = 聚合站兜底
PLAY_BACKENDS = "vinfo,getinfo,aggregate"


# ---------------------------------------------------------------------------
# 【客户端读】数据源在哪 —— 客户端**所有**数据都向它要(取流 / 选集 / 弹幕 / 标题 / 搜索 /
# 轮播 / 热词 / 图片 / 直播频道)。抓取本体全在数据源项目(协议与接口清单见数据源项目说明):
#     本机自测:先跑起数据源项目,这里保持默认地址即可;
#     异地部署:把数据源项目放到那台机器上,这里填它的地址(如 https://your-host/ 或 http://1.2.3.4:8765)。
# 客户端只发 HTTP:不起服务、不占端口,也没有"本机解析"兜底(localplay/ 已删除)。
# 地址填错 / 服务没起来时,界面就是空列表 + "解析失败"提示,不会崩。
# 提醒:上面那批数据源参数(QQ_COOKIE / QQ_GUID / QQ_USE_VINFO / QQ_VAPPID …)是**服务端参数**,
#       服务端读的是同一份 config.json 的 vgapi 段,换 Cookie 仍只改这一个文件。
# ---------------------------------------------------------------------------
PLAY_API_BASE = "http://127.0.0.1:8765"   # 数据服务地址(即数据源);留空 = 没有数据源,一切取不到
PLAY_API_TOKEN = ""                       # 服务端设了 API_TOKEN 时,这里填同一个值(走 X-Api-Token 请求头)
PLAY_API_TIMEOUT = 20                     # 单次请求超时秒数
PLAY_API_CACHE = 60                       # 客户端本地缓存秒数(只缓存取流结果,0 = 不缓存)

# ---------------- 【仅记录,永不执行】启动数据服务的命令行 ----------------
# 数据服务是**独立进程**,得自己起:本机就开个终端敲下面这行,异地部署就登到那台机器上敲。
# 客户端只把本项读进来放着,既不执行它、也不影响任何逻辑(留空 "" 完全可以)——
# 它的作用是把"这个数据源该怎么起"和"它的地址是什么"记在同一处,换源时不用翻文档。
#   数据源:python <数据源项目>/app.py      (默认与上面的 PLAY_API_BASE 对应)
#   本地测试源:python test_server/app.py    (默认 127.0.0.1:8790,不出网,数据全在本地)
PLAY_API_CMD = "python test_server/app.py"


# ---------------------------------------------------------------------------
# 【服务端参数】直播间频道表从哪取(客户端不读它:界面数据来自 GET /live)
# 数据源项目的 live.py 读本项:
#   留空("")    = 用服务端内置清单(实测可播的公开直链);
#   填 http(s)  = 用公开 m3u/m3u8 播放列表(如自己的 IPTV 订阅地址);
#   填本地路径  = 用本地那份播放列表文件(服务端那台机器上的路径)。
#   另外:数据源项目目录下若存在 live.m3u,本项留空时服务端也会自动用它(换源最省事)。
# ---------------------------------------------------------------------------
LIVE_M3U = ""


# ---------------------------------------------------------------------------
# config.json 读取(导入本模块时自动执行一次)
# ---------------------------------------------------------------------------
_JSON_NAME = "config.json"          # 配置文件名(收在"程序目录/config/"下)
_JSON_DIRNAME = "config"            # 配置目录名(与 model/paths.py 的约定保持一致)
_JSON_SECTION = "vgapi"             # 上面这批接口参数所在的段
_JSON_PATH_SECTION = "path"         # 路径类配置(下载目录等)所在的段
_BOOL_KEYS = ("QQ_USE_VINFO", "QQ_STREAM_HTTP", "QQ_COOKIE_CACHE")   # 布尔项:值可写 true/false、1/0、yes/no、on/off


def cfg_path(name):
    """配置文件路径:优先 程序目录/config/ 下的;根部还留着历史版本的旧文件就认旧的(不迁)

    本模块刻意不 import model.paths(注入 run_dir 前它要能独立工作),所以自备一份同名规则,
    与 model.paths._config_path 必须保持一致。
    """
    _new = os.path.join(run_dir(), _JSON_DIRNAME, name)
    _old = os.path.join(run_dir(), name)
    if os.path.isfile(_new) or not os.path.isfile(_old):
        return _new
    return _old


def config_path():
    """程序目录 config/ 下 config.json 的完整路径(全程序唯一的主配置)"""
    return cfg_path(_JSON_NAME)


def _as_bool(_v, _default=False):
    """把配置里的值转成 bool;认不出来就退回默认值"""
    if isinstance(_v, bool):
        return _v
    _s = str(_v).strip().lower()
    if _s in ("1", "true", "yes", "on", "y", "t"):
        return True
    if _s in ("0", "false", "no", "off", "n", "f", ""):
        return False
    return _default


def _typed(_key, _v):
    """按配置项的类型归一化:布尔项转 bool,其余按本模块同名默认值的类型收

    JSON 本事带类型(布尔 / 数字 / 字符串),但"代码里是字符串"的项(如 QQ_VAPPID)仍按字符串收 ——
    免得手写成数字后拼接口参数出岔子。默认值本身是数字的项(如 PLAY_API_TIMEOUT)则原样保留。
    """
    if _key in _BOOL_KEYS:
        return _as_bool(_v, bool(globals().get(_key)))
    _cur = globals().get(_key)
    if isinstance(_cur, str) and not isinstance(_v, str):
        return "" if _v is None else str(_v)
    return _v


def _read_cfg():
    """读 config.json 整份(含 _readme / path / vgapi 等段);文件不存在或读不了返回 None"""
    _p = config_path()
    if not os.path.isfile(_p):   # 兜底:主程序启动时会 os.chdir 到程序目录,这里再按当前目录找一遍(config/ 优先)
        for _c in (os.path.join(os.getcwd(), _JSON_DIRNAME, _JSON_NAME), os.path.join(os.getcwd(), _JSON_NAME)):
            if os.path.isfile(_c):
                _p = _c
                break
        else:
            return None
    try:
        with open(_p, encoding="utf-8-sig") as _f:
            _obj = json.load(_f)
        return _obj if isinstance(_obj, dict) else None
    except Exception as _e:
        print("config.json 读取失败:", _e)
        return None


def _load_json():
    """用 config.json 里 vgapi 段的值覆盖本模块同名默认值

    只覆盖"代码里已经存在的配置项":配置里键名写错会打印提示并忽略,
    不会凭空多出变量,避免手滑(如 QQ_COOKI)导致配置静默失效;
    以 "_" 开头的键(说明文字)一律跳过。
    """
    _cfg = _read_cfg()
    _sec = _cfg.get(_JSON_SECTION) if isinstance(_cfg, dict) else None
    if not isinstance(_sec, dict):
        return False
    for _k, _v in _sec.items():
        _key = str(_k).strip().upper()
        if _key.startswith("_"):
            continue
        if _key not in globals():
            print("config.json 的 %s 段有未知配置项:%s(已忽略)" % (_JSON_SECTION, _k))
            continue
        globals()[_key] = _typed(_key, _v)
    return True


def download_dir():
    """下载目录(config.json 的 path.download_dir):返回纯路径,不含引号

    需要整段拼进播放器命令行的地方自己补一对双引号(见 view/pages/search.py 等);
    配置里没写就用系统"下载"目录。
    """
    _cfg = _read_cfg()
    _sec = _cfg.get(_JSON_PATH_SECTION) if isinstance(_cfg, dict) else None
    _v = str((_sec or {}).get("download_dir") or "").strip().strip('"').strip("'")
    if _v:
        return _v
    return os.path.join(os.path.expanduser("~"), "Downloads").replace("\\", "/")


_load_json()   # 导入时按本文件位置回推的程序目录先读一次;
               # 主程序随后 configure(run_dir=...) 会再读一次(打包运行时以注入的目录为准)
