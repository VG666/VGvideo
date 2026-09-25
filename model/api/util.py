# -*- coding: utf-8 -*-
"""客户端通用小工具(model.api.util)—— 纯文本处理,不含任何网络请求

原来这里叫 net.py,放着通用请求 _http_text 与 Cookie 解析 _cookie_parse。
"所有网络获取下沉到数据服务"之后,这两个函数只服务端在用(数据源项目的请求层),
客户端留着它们就等于留了一条绕过服务端的暗路 —— 已随本次整理删除。
客户端要出网只有一条路:model/api/client.py。

现在本文件只剩两件不打网络的活:
    _json_load(text)     稳健解析数据源返回体(QZOutputJson= 前缀 / 尾部分号 / 夹在 HTML 里都能吃)
    _log_play_url(url)   把即将交给播放器的地址原样打到控制台(复制出来单独验证时很有用)
"""
import sys


def _json_load(text):  # 稳健解析数据源返回体:常带 QZOutputJson= 前缀与尾部分号(直接 loads 会报 Extra data);失败返回 {}
    try:
        _i = text.index("{"); _e = text.rindex("}")
        from json import loads
        return loads(text[_i:_e + 1])
    except Exception:
        return {}


def _log_play_url(u):  # 每次把地址交给播放器之前,原样打到控制台:方便复制出来单独验证(VLC 卡 Opening 时尤其有用)
    _s = str(u or "").strip()
    if not _s:
        return
    if "://" in _s:
        _out = "[播放] 完整地址(%d 字符):\n%s" % (len(_s), _s)
    else:
        _out = "[播放] 本地文件:\n%s" % _s
    try:
        print(_out)
    except Exception:  # 控制台是 GBK 时,带中文的本地路径可能编不出来,退回按 UTF-8 字节写,绝不因为打印失败影响播放
        try:
            _b = getattr(sys.stdout, "buffer", None)
            if _b is not None:
                _b.write((_out + "\n").encode("utf-8", "replace")); _b.flush()
        except Exception:
            pass
