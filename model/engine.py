# -*- coding: utf-8 -*-
"""播放器封装(vlc.py 之上的一层薄壳) —— 一个大类单独成模块

tkPlayer 把 libvlc 的常用操作包成一组直白的方法(播放/暂停/进度/音量/倍速/字幕…),
主程序只跟它打交道,不直接碰 vlc 的 API。

说明:
    - vlc 库缺失(没装/没打包)时 vlc 为 None,实例化 tkPlayer 才会报错,导入本模块不受影响;
    - 需要打印播放地址时,由主程序注入 log_play_url(避免本模块反向 import model.api 造成启动顺序纠缠)。
"""
import platform

try:  # 播放器核心:utility/ 里的 vlc.py(已内置 Py3.11+ 的 getargspec 兼容;paths.py 已把 utility 挂进 sys.path)。打包时随 import 一起收集
    import vlc
except Exception as _vlc_err:
    vlc = None
    print("警告:vlc 播放器库导入失败:", _vlc_err)

# 主程序启动时注入(一般为 model.api 里的 _log_play_url):每次把地址交给播放器前打一行到控制台
log_play_url = None


def _log_play_url(u):
    if log_play_url is None:
        return
    try:
        log_play_url(u)
    except Exception:
        pass


class tkPlayer:

    def __init__(self, *args):
        if args:
            instance = vlc.Instance(*args)
            self.media = instance.media_player_new()
        else:
            self.media = vlc.MediaPlayer()

    # 设置待播放的url地址或本地文件路径，每次调用都会重新加载资源
    def set_uri(self, uri):
        _log_play_url(uri)   # 每次开播/换集都会走这里:把地址打到控制台
        self.media.set_mrl(uri)

    # 播放 成功返回0，失败返回-1
    def play(self, path=None):
        if path:
            self.set_uri(path)
            return self.media.play()
        else:
            return self.media.play()

    # 暂停
    def pause(self):
        self.media.pause()

    # 恢复
    def resume(self):
        self.media.set_pause(0)

    # 停止
    def stop(self):
      try:
        self.media.stop()
      except:
        pass

    # 释放资源
    def release(self):
      for _ in range(3):#最多重试3次:旧写法 while True 一旦 release 反复报错就会把窗口卡死
        try:
          self.media.release()
          return
        except:
          pass

    # 是否正在播放
    def is_playing(self):
        return self.media.is_playing()

    # 已播放时间，返回毫秒值
    def get_time(self):
        return self.media.get_time()

    # 拖动指定的毫秒值处播放。成功返回0，失败返回-1 (需要注意，只有当前多媒体格式或流媒体协议支持才会生效)
    def set_time(self, ms):
        return self.media.get_time()

    # 音视频总长度，返回毫秒值
    def get_length(self):
        return self.media.get_length()

    # 获取当前音量（0~100）
    def get_volume(self):
        return self.media.audio_get_volume()

    # 设置音量（0~100）
    def set_volume(self, volume):
        return self.media.audio_set_volume(volume)

    # 返回当前状态：正在播放；暂停中；其他
    def get_state(self):
        state = self.media.get_state()
        if state == vlc.State.Playing:
            return 1
        elif state == vlc.State.Paused:
            return 0
        else:
            return -1

    # 当前播放进度情况。返回0.0~1.0之间的浮点数
    def get_position(self):
        return self.media.get_position()

    # 拖动当前进度，传入0.0~1.0之间的浮点数(需要注意，只有当前多媒体格式或流媒体协议支持才会生效)
    def set_position(self, float_val):
        return self.media.set_position(float_val)

    # 获取当前文件播放速率
    def get_rate(self):
        return self.media.get_rate()

    # 设置播放速率（如：1.2，表示加速1.2倍播放）
    def set_rate(self, rate):
        return self.media.set_rate(rate)

    # 设置宽高比率（如"16:9","4:3"）
    def set_ratio(self, ratio):
        self.media.video_set_scale(0)  # 必须设置为0，否则无法修改屏幕宽高
        self.media.video_set_aspect_ratio(ratio)

    # 设置窗口句柄
    def set_window(self, wm_id):
        if platform.system() == 'Windows':
            self.media.set_hwnd(int(wm_id))#Windows下必须用set_hwnd把渲染窗口绑到控件句柄,写错方法名会导致视频不嵌入(跑到独立窗口或黑屏)
        else:
            self.media.set_xwindow(wm_id)

    # 注册监听器
    def add_callback(self, event_type, callback):
        self.media.event_manager().event_attach(event_type, callback)

    # 移除监听器
    def remove_callback(self, event_type, callback):
        self.media.event_manager().event_detach(event_type, callback)

    def set_marquee(self):
      while True:
        try:
          self.media.video_set_marquee_int(vlc.VideoMarqueeOption.Enable, 1)
          self.media.video_set_marquee_int(vlc.VideoMarqueeOption.Size, 28)
          self.media.video_set_marquee_int(vlc.VideoMarqueeOption.Color, 0xff0000)
          self.media.video_set_marquee_int(vlc.VideoMarqueeOption.Position, vlc.Position.Bottom)
          self.media.video_set_marquee_int(vlc.VideoMarqueeOption.Timeout, 0)
          self.media.video_set_marquee_int(vlc.VideoMarqueeOption.Refresh, 10000)
        except:
          break
    def update_text(self, content):
        self.media.video_set_marquee_string(vlc.VideoMarqueeOption.Text, content)


__all__ = ["tkPlayer", "vlc", "log_play_url", "_log_play_url"]
