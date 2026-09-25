# -*- coding: utf-8 -*-
"""占位封面生成(test_server.cover)

测试数据源没有真实海报,又要让界面上的海报位不空着,所以按"种子"现算一张 PNG:

    cover:xxx  →  同一串种子永远得到同一张图(颜色、条纹、播放三角都跟着种子走)
    纯标准库实现(zlib + struct 手写 PNG),不依赖 Pillow —— 测试数据源要能裸装即用。

给 /image 用:客户端拿到 img 字段后,会把它原样塞进 /image?url=<img> 来取图,
所以目录(catalog.py)里把海报写成 "cover:剧集id" 这种自带种子的标记就行,不需要任何外部图片。

注意:**标记不能直接发给客户端**。客户端 fetch_image 见到字符串里没有 "://" 时,
会把它当成"本地文件路径"交给 PIL 打开,所以 app.py 发响应前一定会把
"cover:剧集id" 翻成 http://…/cover/剧集id.png,再交给客户端。
"""
import hashlib
import colorsys
import struct
import zlib

_DEF_W = 256          # 默认尺寸:客户端自己会用 PIL 缩放到控件大小,这里不必大
_DEF_H = 144
_CACHE = {}           # 种子 -> PNG 字节(同一个种子只算一次)


def _seed_num(seed):
    """种子 → 稳定整数(同一个种子每次都是同一个数)"""
    return int(hashlib.md5(str(seed).encode("utf-8")).hexdigest()[:8], 16)


def _chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def _encode(w, h, rows):
    """把逐行 RGB 字节编成 PNG(24 位真彩)"""
    _raw = b"".join(b"\x00" + _r for _r in rows)          # 每行前面补一个 filter 字节 0
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(_raw, 6))
            + _chunk(b"IEND", b""))


def png(seed="", w=_DEF_W, h=_DEF_H):
    """按种子生成一张占位封面(返回 PNG 字节);同一个种子结果完全一致"""
    _key = (str(seed), int(w), int(h))
    _hit = _CACHE.get(_key)
    if _hit:
        return _hit
    _n = _seed_num(seed)
    # 基色随种子走:同一个剧集每次打开都是同一个颜色,截图/录屏时好认
    _hue = (_n % 360) / 360.0
    _r0, _g0, _b0 = colorsys.hsv_to_rgb(_hue, 0.55, 0.62)
    _r1, _g1, _b1 = colorsys.hsv_to_rgb((_hue + 0.08) % 1.0, 0.75, 0.30)
    _stripe = 0.055 * (1 if (_n >> 8) & 1 else -1)         # 斜条纹:明暗方向也随种子
    # 播放三角(近白),按中心点与三个半平面判定
    _cx, _cy = w * 0.5, h * 0.5
    _sz = min(w, h) * 0.30
    _ax, _ay = _cx - _sz * 0.62, _cy - _sz
    _bx, _by = _cx - _sz * 0.62, _cy + _sz
    _dx, _dy = _cx + _sz * 0.75, _cy
    _rows = []
    for _y in range(h):
        _t = (_y + 1) / float(h)
        _br, _bg, _bb = (int(255 * (_r0 + (_r1 - _r0) * _t)),
                         int(255 * (_g0 + (_g1 - _g0) * _t)),
                         int(255 * (_b0 + (_b1 - _b0) * _t)))
        _row = bytearray()
        for _x in range(w):
            _p = 0.0
            if ((_x + _y) // 24) % 2 == 0:                 # 24px 宽的斜条纹
                _p = _stripe
            if _p:
                _row += bytes((max(0, min(255, int(_br * (1 + _p)))),
                               max(0, min(255, int(_bg * (1 + _p)))),
                               max(0, min(255, int(_bb * (1 + _p))))))
                continue
            _inside = False
            if _y >= _ay - 1 and _y <= _by + 1 and _x >= _ax - 1 and _x <= _dx + 1:
                # 三条边各判一次"点在同侧":三次同号即在三角形内(不依赖顶点的绕向)
                _d1 = (_bx - _ax) * (_y - _ay) - (_by - _ay) * (_x - _ax)
                _d2 = (_dx - _bx) * (_y - _by) - (_dy - _by) * (_x - _bx)
                _d3 = (_ax - _dx) * (_y - _dy) - (_ay - _dy) * (_x - _dx)
                _inside = ((_d1 >= 0 and _d2 >= 0 and _d3 >= 0)
                           or (_d1 <= 0 and _d2 <= 0 and _d3 <= 0))
            if _inside:
                _row += bytes((min(255, _br + 90), min(255, _bg + 90), min(255, _bb + 90)))
            else:
                _row += bytes((_br, _bg, _bb))
        _rows.append(bytes(_row))
    _b = _encode(w, h, _rows)
    _CACHE[_key] = _b
    return _b
