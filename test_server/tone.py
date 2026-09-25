# -*- coding: utf-8 -*-
"""占位音轨生成(test_server.tone)

测试数据源没有真实视频,但"到底能不能播"这件事必须有个**真的能播**的东西来验 ——
于是用标准库手写一段 16 位单声道 WAV(VLC 认这个格式:进度条、暂停、倍速、
换集都能真的动起来,和播真视频走的是同一条链路):

    每 5 秒换一次音高:前 4.5 秒低音,最后 0.5 秒高音(听得到"滴"的一声)。
    所以听到声音变了,就说明播放进度是真的在往前走,不是卡在 0 秒。

纯标准库(array + math + struct):不装 ffmpeg、不联网、不依赖任何第三方包。
想要真画面?往 test_server/media/ 里丢一个 mp4 就行,app.py 会优先用它(见 /media/stream)。
"""
import array
import math
import struct

_DEF_SECONDS = 60          # 默认音轨长度(够看完一次"续播/拖动进度"的验证)
_DEF_RATE = 8000           # 采样率:8kHz 单声道足够听个响,一分钟也才 960KB
_CACHE = {}                # (秒数, 采样率) -> WAV 字节;同一参数只算一次


def _header(n_samples, rate):
    """44 字节的 WAV 头(PCM / 单声道 / 16 位)"""
    _bytes = n_samples * 2
    return (b"RIFF" + struct.pack("<I", 36 + _bytes) + b"WAVE"
            + b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", _bytes))


def wav(seconds=_DEF_SECONDS, rate=_DEF_RATE):
    """生成一段可播放的测试音轨(返回 WAV 字节);同参数结果完全一致"""
    _key = (int(seconds), int(rate))
    _hit = _CACHE.get(_key)
    if _hit:
        return _hit
    _n = int(rate * seconds)
    _pcm = array.array("h", bytes(2 * _n))       # 预分配后按下标写,比逐个 append 快得多
    _step = 2.0 * math.pi / rate
    for _i in range(_n):
        _phase = (_i / float(rate)) % 5.0
        _low = _phase < 4.5                      # 前 4.5 秒低音,后 0.5 秒高音
        _pcm[_i] = int((9000 if _low else 13000) * math.sin(_step * (440.0 if _low else 880.0) * _i))
    _b = _header(_n, rate) + _pcm.tobytes()
    _CACHE[_key] = _b
    return _b
