# -*- coding: utf-8 -*-
"""图片 / 文本兼容工具 —— 一个大类单独成模块

    Picture_transcoding   图片自适应(等比缩放后贴到给定框内)
    with_surrogates       把 BMP 外字符转成代理对(Tk 老版本对 4 字节字符支持不稳)
    _safe_attributes      逐个尝试设置窗口 attributes,当前平台不支持的项直接跳过

窗口 / 任务栏 / 程序坞图标见 view/icons.py 的 App_icon。
"""
import re

from PIL import Image

_nonbmp = re.compile(r'[\U00010000-\U0010FFFF]')


def _surrogatepair(match):
    char = match.group()
    assert ord(char) > 0xffff
    encoded = char.encode('utf-16-le')
    return (
        chr(int.from_bytes(encoded[:2], 'little')) + 
        chr(int.from_bytes(encoded[2:], 'little')))


def with_surrogates(text):
    return _nonbmp.sub(_surrogatepair, text)


try:
    _LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    _LANCZOS = Image.ANTIALIAS


def Picture_transcoding(w, h, w_box, h_box, pil_image):  # 图片自适应算法
      f1 = 1.0*w_box/w  # 先化成浮点数再除以当前的高
      f2 = 1.0*h_box/h  # 先化成浮点数再除以当前的高
      factor = min([f1, f2])  # 创建设定对象
      width = int(w*factor)  # 化为整数
      height = int(h*factor)  # 化为整数
      return pil_image.resize((width, height), _LANCZOS)  # 转换


def _safe_attributes(window, *attr_sets):  # 逐个尝试设置窗口attributes;某属性当前平台不支持(如Windows透明色)就忽略,不让程序崩
    for attr_set in attr_sets:
        try:
            window.attributes(*attr_set)
        except Exception:
            pass


__all__ = ["_nonbmp", "_surrogatepair", "with_surrogates", "_LANCZOS",
           "Picture_transcoding", "_safe_attributes"]
