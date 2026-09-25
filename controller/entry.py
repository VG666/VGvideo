# -*- coding: utf-8 -*-
"""启动器(从 main.py 拆出)

把 "video.exe 2 剧集id 下载目录" 这类命令行参数解析成运行期状态,再打开播放器窗口。
源码运行与打包运行走的是同一条路。

    VGvideo(x)            参数解析 + 打开播放窗口(已有窗口开着时不重复开)
    reset_windows_opened  播放器关窗时把"已开窗口数"清零
    seek_on_arrow         左右方向键松开时把进度对齐到进度条

这里同时负责几处"接线":观看记录取当前播放器、播放地址日志出口。
"""
import os
from sys import argv as _sys_argv

import model.records as records
import model.engine as engine
import model.state as state
from model.records import _rec_read, _rec_save
from model.api import _log_play_url

# --- 接线:观看记录需要"当前打开中的播放器",播放器需要统一的地址日志出口 ---
records.get_active_player = lambda: state.active_player
engine.log_play_url = _log_play_url


def reset_windows_opened():#关闭播放器窗口时把已开窗口计数清零(原 exec 设置全局)
    state.opened_windows=0


def seek_on_arrow(player, scale, event, resume_flag):#左右方向键松开时把播放进度对齐到进度条位置(原 exec 代码)
    if event.keycode==37 or event.keycode==39:
        while True:
            player.set_position(scale.get()/10000)
            if float(str(player.get_position())[:len(str(scale.get()/10000))-1])==float(str(scale.get()/10000)[:len(str(scale.get()/10000))-1]):
                if resume_flag==1:
                    player.resume()
                break




def VGvideo(x):#之前本想用命令行调用播放器,现在改为改写argv模拟命令行传参再启动播放器;源码运行与打包运行走同一条路
    try:
        if state.opened_windows!=0:#已有播放器窗口开过/开着,不再重复开
            return
        x=str(x)
        if "video.exe" not in x:
            return
        _cmd=x.split("video.exe",1)[1].strip()            # 形如: 2 cid "路径" / 1 "本地文件" 4 / 3 地址 "路径" / 4 地址
        _mode=_cmd.split(" ",1)[0] if " " in _cmd else _cmd
        _rest=_cmd[len(_mode):].strip() if len(_mode)<len(_cmd) else ""
        _path=_rest.split('"')[1] if '"' in _rest else "" # 引号里的部分一般是下载目录或本地文件
        if _mode=="1":   # 播放本地文件
            _mid=_rest.split('"')[1] if '"' in _rest else _rest.strip()
            state.argv=["video.exe","1",str(_mid).replace("/","\\"),"4"]
            state.current_episode=0
        elif _mode=="4": # 直播/网页流地址
            _mid=(_rest.split('"')[0].strip() or (_rest.split('"')[1] if '"' in _rest else _rest.strip()))
            state.argv=["video.exe","4",_mid,""]
            state.current_episode=0
        elif _mode in ("2","3"): # 2=剧集(cid), 3=单视频(地址/标识)
            _mid=_rest.split('"')[0].strip()
            _download=_path.replace("/","\\")
            state.argv=["video.exe",_mode,_mid,_download]
            state.current_episode=0
            if _mode=="2":
                _r=_rec_read(_mid)#观看记录(JSON 格式;历史 .ini / .vgini 记录也能读)
                if _r is None:#没有记录:先建一份,从第1集开始
                    _rec_save(_mid,episode=0,progress=0.0)
                    state.current_episode=0
                else:
                    state.current_episode=int(_r.get("episode") or 0)
        else:
            return
        if state.opened_windows==0:
            state.opened_windows=1
            _vg_main=state.main_window
            if _vg_main is not None:#主窗口在:切回 Tk 主线程再建播放窗口(控件只能在主线程创建)
                _vg_main.window.after(1,lambda:_open_player_window(1))
            else:#主窗口还没登记:直接开,免得这次点击被静默吞掉
                _open_player_window(1)
    except Exception as _vg_err:
        print("VGvideo 参数解析失败:",_vg_err)
# ===== 无边框窗口公共逻辑 Window_chrome 见 view/chrome.py =====#



def _open_player_window(_arg=1):
    """打开播放器窗口(函数内 import:view.player.app 要用到本模块的启动器,彼此延迟引用)"""
    from view.player.app import App
    return App(1)
