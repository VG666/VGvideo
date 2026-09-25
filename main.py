# -*- coding: utf-8 -*-
"""VG视频 —— 程序入口。

这是个**装得下任何视频源的壳子**:界面要的每一份数据都只向一个 HTTP 地址要
(config/config.json 的 vgapi.PLAY_API_BASE),所以"换源"就是改那一个地址,
客户端这里一行都不用动。可以换的数据源至少有两个:
    数据源项目/   真实取流 / 搜索 / 直播的服务端(独立项目,不随客户端发布)
    test_server/   本地测试源:完全不出网,数据全在本地现造,用来验证"换个源照样能跑"

项目按 MVC 三层组织,本文件只做"程序入口"该做的三件事:启动环境 → 接口接线 → 进主界面。

    model/          M:数据与业务(不画界面)
        state.py      跨模块共享状态(原来散落各处的 global 全部集中到这里)
        paths.py      程序目录 / 数据文件路径
        records.py    观看记录(Recordset/<剧集id>.json)
        engine.py     VLC 播放引擎封装
        download.py   aria2 + ffmpeg 下载
        api/          只负责"获取":把要的数据向**数据源**要回来(取流 / 选集 / 弹幕 / 标题 /
                      搜索 / 轮播 / 热词 / 图片 / 直播频道);抓取本体全在数据源那边,客户端一律不出网

    view/           V:界面(画控件 + 绑回调)
        chrome.py     无边框窗口公共逻辑 + 输入框剪贴板助手
        image.py      图片缩放 / 窗口图标
        widgets/      通用控件:搜索框 / 标题栏 / 左侧导航 / 轮播 / 选集 / 联想词
        pages/        页面:主窗口(VG_video) / 首页 / 搜索结果 / 观看记录 / 咪咕直播
        player/       播放器窗口:按职责拆成 6 个 mixin,由 app.py 组装成 App

    controller/     C:流程控制
        entry.py      命令行参数解析 + 打开播放器窗口

根目录只留运行期文件:main.py(程序入口)、videovlc/(libvlc 动态库)、ico/(程序图标 logo.ico),以及数据目录 Recordset/ 与 rotation_local/;
VLC 绑定与 Tk 小工具(vlc.py / max_win.py / windnd.py / ToolTips.py)统一收在 utility/ 里——
它们仍按顶层模块用(import vlc / import max_win …):model/paths.py 启动时会先把 utility/ 挂进 sys.path;
手动跑的工具也收在 utility/ 里(add_record_names.py),
顺手把 aria2c.exe / ffmpeg.exe 丢进 utility/ 也能被自动用上,见 model/download.py;
配置统一收在 config/ 里 —— config.json(人工维护:path / vgapi 等段)+ uiprefs.json(程序自维护的界面偏好);
老版本的 config.ini / file.ini / uiprefs.ini 首次启动会自动升级进这两个 JSON 并删除(摊在根目录也能认);
调试与自测脚本统一收在 test/ 里(play.py / test_qq.py / search_api.py)。
数据源有两套,都收在自己目录里,**都是命令行单独启动**(客户端不会替你起服务):
    python <数据源项目>/app.py     数据源服务,默认 127.0.0.1:8765,要真实内容时用它(详见数据源项目说明)
    python test_server/app.py   本地测试源,默认 127.0.0.1:8790,不出网,验证"换源客户端原样能跑"(详见 test_server/app.py 开头)
启动命令本身也记在 config/config.json 的 vgapi.PLAY_API_CMD 里 —— 那一项只是记录,程序永远不会执行它。

运行:python main.py
"""
import os
from sys import argv

# ===================================================================== 1. 启动环境
from model.paths import application_path, _run_dir, _ensure_data_files

os.environ['PYTHON_VLC_MODULE_PATH'] = f"{application_path}\\videovlc"  # vlc 库目录,须在导入 model.engine 前设好
_ensure_data_files()          # 建好 config/ 与 Recordset,并把历史 ini 归拢/升级进 config/ 的 JSON(升级后删除 ini)
try:
    os.chdir(_run_dir)        # 兼容所有相对路径(config/、Recordset 等)
except Exception:
    pass

# ===================================================================== 2. 接口层接线
# 所有网络接口统一收在 model/api 里;这里用 `import *` 把接口名同时留在本模块命名空间,
# 使 test/ 下的 test_qq.py / play.py 这类脚本 `import main` 后仍能直接取用(main._resolve_url 等)。
from model.api import *

try:                          # 把"程序目录"告诉接口层:config/config.json 与 Recordset 都以它为准
    configure(run_dir=_run_dir)
except Exception as _cfg_err:
    print("接口层程序目录注入失败:", _cfg_err)

try:                          # 播放器核心:utility/ 里的 vlc.py(paths.py 已把 utility 挂进 sys.path;打包时记得 --paths utility)
    import vlc
except Exception as _vlc_err:
    vlc = None
    print("警告:vlc 播放器库导入失败:", _vlc_err)

import model.engine as engine
engine.log_play_url = _log_play_url   # 播放地址打印统一走 model.api 的 _log_play_url

# =========================================== 3. 数据来源(客户端只"获取",不再自建服务)
# 取流 / 选集 / 弹幕 / 标题 / 搜索 / 轮播 / 热词 / 图片 / 直播频道,全部由**数据源**提供:
#     数据源地址 = config/config.json 的 vgapi.PLAY_API_BASE
#     数据源 python <数据源项目>/app.py / 本地测试源 python test_server/app.py(8790),接口清单见数据源项目说明
# 客户端只发 HTTP 请求:不起服务、不占端口,也没有"本机解析"兜底 —— 本地模式与自启服务已彻底移除,
# 所以"数据到底从哪来"永远只有一个答案:PLAY_API_BASE 指向的那台服务。
# 服务没起来时:model/api 的接口一律返回空值(界面显示空列表 / 提示解析失败),不会崩。


# ===================================================================== 4. 页面 / 窗口
from view.icons import App_icon
App_icon.use_process_identity()         # 任务栏身份(必须早于建窗口):任务栏才会认程序自己的 logo
from view.pages.main import VG_video    # 主窗口 / 首页
from view.player.app import App         # 播放器窗口(由 view/player/ 的 6 个 mixin 组装)

# ===================================================================== 5. 程序入口
if __name__ == '__main__':
    if len(argv) == 1:                  # 无参数:正常启动主界面(VG_video().start() 内部进入 mainloop)
        VG_video().start()
