# -*- coding: utf-8 -*-
"""左侧导航 / 首页"大家在看"标签的取用助手(从 main.py 拆出)

原来靠 globals().get("Left_option_"+str(n)) 拼名字取控件;拆成多文件后各模块的
globals() 互不相通,所以改走 model.state 里的注册表(键就是原来的序号)。
"""
import model.state as state


def nav_button(n):
    """按序号取左侧导航按钮(1..12);没建好就返回 None"""
    return state.nav_buttons.get(n)


def trending_label(n):
    """按序号取首页"大家在看"文字标签(1..7);没建好就返回 None"""
    return state.trending_labels.get(n)


Left_option_at = nav_button                    # 老名字,兼容
Home_rotation_right_Label_at = trending_label



