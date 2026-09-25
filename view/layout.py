# -*- coding: utf-8 -*-
"""主窗口布局骨架 —— 尺寸/坐标算式集中在这一处

为什么单独成模块
    拆分前"留多少边、导航多宽、内容区摆哪"这类算式散在 VG_video.start /
    Page_switching / Search 和左侧导航里,同一个式子(如 w//5、h//10)抄了十来遍。
    想让内容区往左挪一点,得同时改好几处,漏改一处就会出现"切页后位置不一致"
    的错位 —— 现在算式只写在这里,调用处用函数表达意图,数值改了全局一起变。

坐标系约定(与原实现完全一致,改这里等于改全局)
    左侧导航约一屏宽的 1/10,内容区左边界 x = w//5
    顶部条约一屏高的 1/10,  内容区上边界 y = h//10
    两个方向再各让出 3px 给窗口边缘的缩放热区,内容不会压住缩放条

用法
    new_content_frame(window, RELAYOUT_HOME)         建一块内容区并摆好
    place_content(frame, window, RELAYOUT_WIDE)      只重摆位置(窗口尺寸变了)
    nav_place_kw(window, rely)                       左侧导航项的 place 参数
"""
from tkinter import Frame


# --------------------------------------------------------------------------- #
# 主窗口内容区(vgFrame)
# --------------------------------------------------------------------------- #
CONTENT_X_DIV = 5            # 内容区左边界 = 窗口宽 // 5(左侧让给导航)
CONTENT_Y_DIV = 10           # 内容区上边界 = 窗口高 // 10(上方让给标题条)
CONTENT_EDGE = 3             # 再让出 3px,免得内容盖住窗口边缘的缩放热区

CONTENT_WIDTH_DIV = 46       # 内容区配置宽 = (窗口宽 // 46) * 35.5
CONTENT_WIDTH_RATE = 35.5
CONTENT_HEIGHT_DIV = 30      # 内容区配置高 = (窗口高 // 30) * 27.3
CONTENT_HEIGHT_RATE = 27.3

SEARCH_SCREEN_W_DIV = 4      # 搜索页按屏幕尺寸算配置宽高(历史遗留:与窗口尺寸那套略有出入)
SEARCH_SCREEN_H_DIV = 6
SEARCH_WIDTH_RATE = 36.5

RELAYOUT_HOME = 0.95         # 首页/普通页面:右边留一点空
RELAYOUT_WIDE = 0.99         # 直播/历史/搜索:几乎铺满


def content_frame_size(window):
    """新建 vgFrame 时用的配置宽高(返回字符串,与原 f-string 写法一致)。"""
    return (f"{(window.winfo_width() // CONTENT_WIDTH_DIV) * CONTENT_WIDTH_RATE}",
            f"{(window.winfo_height() // CONTENT_HEIGHT_DIV) * CONTENT_HEIGHT_RATE}")


def screen_content_frame_size(window):
    """搜索结果页:按屏幕(而不是当前窗口)尺寸算配置宽高。"""
    _w = window.winfo_screenwidth() - window.winfo_screenwidth() // SEARCH_SCREEN_W_DIV
    _h = window.winfo_screenheight() - window.winfo_screenheight() // SEARCH_SCREEN_H_DIV
    return (f"{(_w // CONTENT_WIDTH_DIV) * SEARCH_WIDTH_RATE}",
            f"{(_h // CONTENT_HEIGHT_DIV) * CONTENT_HEIGHT_RATE}")


def content_place(window, relwidth=RELAYOUT_WIDE, anchor='nw'):
    """vgFrame.place(...) 的参数:窗口一改尺寸就按新尺寸重算一遍。"""
    _w, _h = window.winfo_width(), window.winfo_height()
    return dict(x=_w // CONTENT_X_DIV,
                y=_h // CONTENT_Y_DIV,
                relwidth=relwidth,
                width=-(_w // CONTENT_X_DIV) - CONTENT_EDGE,
                relheight=1,
                height=-(_h // CONTENT_Y_DIV) - CONTENT_EDGE,
                anchor=anchor)


def place_content(frame, window, relwidth=RELAYOUT_WIDE, anchor='nw'):
    """把内容区摆到主窗口上(窗口缩放后重摆也走这里)。"""
    frame.place(**content_place(window, relwidth, anchor))


def bind_content_resize(frame, window, relwidth=RELAYOUT_WIDE, anchor='nw'):
    """窗口尺寸变化时自动把内容区重新贴回原位。"""
    def _replace(_event=None):
        frame.place(**content_place(window, relwidth, anchor))
    frame.bind("<Configure>", _replace)
    return _replace


def new_content_frame(window, relwidth=RELAYOUT_WIDE, bg=None, on_screen=False):
    """按当前窗口尺寸建一块内容区(vgFrame)、摆好并挂上自动重摆,直接返回。"""
    _size = screen_content_frame_size(window) if on_screen else content_frame_size(window)
    _kw = {} if bg is None else {"bg": bg}
    _frame = Frame(window, width=_size[0], height=_size[1], **_kw)
    place_content(_frame, window, relwidth)
    bind_content_resize(_frame, window, relwidth)
    return _frame


# --------------------------------------------------------------------------- #
# 左侧导航
# --------------------------------------------------------------------------- #
NAV_WIDTH_DIV = 6.1          # 导航项宽 = 窗口宽 // 6.1
NAV_HEIGHT_DIV = 20          # 导航项高 = 窗口高 // 20
NAV_FONT_DIV = 51.25         # 导航项字号 = 窗口宽 // 51.25(取负号再传入)
NAV_RELY_DIV = 27            # 纵坐标 = 序号 / 27
NAV_RELHEIGHT = 1 / 15       # 导航项高度占窗口高的比例
NAV_ITEM_RELY = {"first": 2 / 27, "join": 24 / 27}   # 首项与"加入组织"的纵坐标


def nav_font(window, bold=True):
    """导航项字体:字号跟着窗口宽度走。"""
    return scaled_font(window, NAV_FONT_DIV, "Comic Sans MS", bold)


def nav_place_kw(window, rely):
    """导航项的 place 参数:横向贴左,纵向按 rely 排在窗口高度上。"""
    return dict(x=0, rely=rely / NAV_RELY_DIV,
                y=window.winfo_height() // NAV_HEIGHT_DIV,
                relheight=NAV_RELHEIGHT)


def nav_item_size(window):
    """导航项的配置宽高:(宽, 高)。"""
    return window.winfo_width() // NAV_WIDTH_DIV, window.winfo_height() // NAV_HEIGHT_DIV


# --------------------------------------------------------------------------- #
# 标题条左侧:底色块 + 程序图标 + "VG视频"
# --------------------------------------------------------------------------- #
TITLE_BAR_WIDTH_DIV = 6          # 底色块宽 = 窗口宽 // 6
TITLE_BAR_HEIGHT_DIV = 9.1       # 底色块高 = 窗口高 // 9.1(比上面一行略矮,原样保留)
TITLE_LOGO_WIDTH_DIV = 6.1       # 文字块宽 = 窗口宽 // 6.1
TITLE_LOGO_HEIGHT_DIV = 9        # 文字块高 = 窗口高 // 9
TITLE_LOGO_FONT_DIV = 35         # "VG视频"字号 = 窗口宽 // 35
TITLE_LOGO_IMAGE_DIV = 10        # 图标边长 = 窗口高 // 10


def title_bar_width(window):
    """标题条最左侧底色块的宽度。"""
    return window.winfo_width() // TITLE_BAR_WIDTH_DIV


def title_bar_height(window):
    """标题条最左侧底色块的高度。"""
    return window.winfo_height() // TITLE_BAR_HEIGHT_DIV


def title_logo_size(window):
    """「VG视频」文字块的配置宽高:(宽, 高)。"""
    return (window.winfo_width() // TITLE_LOGO_WIDTH_DIV,
            window.winfo_height() // TITLE_LOGO_HEIGHT_DIV)


def title_logo_font(window):
    """「VG视频」的字体,字号跟着窗口宽度走(文字不加粗,与原样式一致)。"""
    return scaled_font(window, TITLE_LOGO_FONT_DIV, "Comic Sans MS", False)


def title_logo_image_size(window):
    """标题条上程序图标的边长(正方形)。"""
    return window.winfo_height() // TITLE_LOGO_IMAGE_DIV


# --------------------------------------------------------------------------- #
# 标题条:logo 行上的搜索框 / 右上角三键
# --------------------------------------------------------------------------- #
CONTROL_RELX = 0.855            # 三键容器横向位置(离窗口左边的比例)
CONTROL_PAD_DIV = 205            # 三键之间的间距 = 窗口宽 // 205
TITLE_CONTROL_OFFSET = 25        # 三键纵坐标:标题条高的一半再减 25

CONTROL_FONT_DIV_MENU = 37       # 三键字号 = 窗口宽 // N(字族与是否加粗照旧)
CONTROL_FONT_DIV_MINIMIZE = 55
CONTROL_FONT_DIV_MAXIMIZE = 49
CONTROL_FONT_DIV_CLOSE = 38

# 搜索框:整框尺寸只有一个来源 —— 窗口尺寸。高由窗口高算,宽由窗口宽算,
# 框内的留白/圆角/字号再全部由"画布高"推算,所以换屏幕、换分辨率、拉窗口
# 都不会出现"框跟着变大、字却还是 1080p 那会儿大小"的错位。
SEARCHBOX_WIDTH_DIV = 2.5625     # 搜索框画布宽 = 窗口宽 / 2.5625
SEARCHBOX_HEIGHT_DIV = 20        # 搜索框画布高 = 窗口高 // 20
SEARCHBOX_PAD_DIV = 9            # 框内留白 = 画布高 // 9(圆角矩形左/上边界 + 输入框纵向留白)
SEARCHBOX_RADIUS_DIV = 15        # 圆角半径 = 画布高 - 画布高 // 15 * 2
SEARCHBOX_BUTTON_DIV = 5         # 「全网搜」按钮的字号 = 画布高 // 5 * 2(位置见 searchbox_text_pos)
SEARCHBOX_RELX = 0.23            # 搜索框横向位置
INPUT_RELWIDTH_NORMAL = 0.67     # 输入框在画布里的宽度占比(窗口最大化时用 0.7)
INPUT_RELWIDTH_MAXIMIZED = 0.7


def scaled_font(window, div, family="Verdana", bold=True):
    """字号跟着窗口宽度走的字体(负数 = 按像素算)。"""
    _size = int(window.winfo_width() // div) * -1
    return (family, _size, "bold") if bold else (family, _size)


def title_item_y(title_widget, offset):
    """标题条上某控件的纵坐标:取标题条高度的一半,再往上微调 offset。"""
    return int((title_widget["height"] // 2) - offset)


def title_center_y(title_widget, item_height):
    """标题条上某控件垂直居中的纵坐标(item_height = 控件自身高度)。

    和 title_item_y 的区别:这里的偏移量不是写死的像素,而是控件高度的一半,
    所以控件长高了它也自动跟着居中,不挑分辨率。
    """
    return int(int(title_widget["height"]) // 2 - item_height / 2)


def control_pad(window):
    """右上角三键之间的间距。"""
    return window.winfo_width() // CONTROL_PAD_DIV


def searchbox_width(window):
    """搜索框画布的宽度。"""
    return int(window.winfo_width() / SEARCHBOX_WIDTH_DIV)


def searchbox_height(window):
    """搜索框画布的高度:跟着窗口高等比,窗口一大整框跟着放大。"""
    return window.winfo_height() // SEARCHBOX_HEIGHT_DIV


def searchbox_metrics(height):
    """搜索框内部的留白 / 圆角 / 按钮字号,全部由画布高推出来。

    比 height=45(1080p 默认窗口)时:留白 5、圆角 39、遮挡矩形左边界 40、按钮字号 -18,
    与拆分前写死的像素一致 —— 那些数值本来就是照着"画布高的几分之几"估的。
    """
    _btn = height // SEARCHBOX_BUTTON_DIV * 2     # 按钮字号(45 → 18)
    return dict(pad=height // SEARCHBOX_PAD_DIV,                     # 圆角矩形左/上边界(45 → 5)
                radius=height - height // SEARCHBOX_RADIUS_DIV * 2,  # 圆角半径(45 → 39)
                occluder_x=height - height // SEARCHBOX_PAD_DIV,     # 遮挡矩形左边界,让出一个留白(45 → 40)
                button_font=-_btn)                                   # 按钮文字字号(负数 = 按像素算)


SEARCHBOX_COVER_MUL = 2.85       # 输入框底色覆盖层的右边界 = 画布宽 // 4 * 2.85(按钮可见区从这里开始)


def searchbox_cover_x(width):
    """输入框底色那两块深色覆盖区的右边界 —— 也就是「全网搜」按钮可见区的左边界。"""
    return int(width // 4 * SEARCHBOX_COVER_MUL)


def searchbox_text_pos(width, height, input_relwidth):
    """「全网搜」按钮文字的位置:(x, y),落在按钮可见区的正中间。

    横向:按钮可见区 = 覆盖层右边界 / 输入框控件右边界里更靠右的那个(输入框是 place
        出来的,起始 x 让出半个画布高)到画布右边界,取中点。原来是写死的算式,
        窗口一拉宽文字就偏右。
    纵向:圆角框占 pad..height,中心是 (pad + height) / 2。原来的 _h//12*8.5 是台阶式的
        近似(45 → 25 正好,height 一变大就整体偏低)。
    """
    _m = searchbox_metrics(height)
    _left = max(searchbox_cover_x(width), height // 2 + int(width * input_relwidth))
    return (int((_left + width) / 2), int((_m["pad"] + height) / 2))


def input_place_kw(search_canvas, relwidth):
    """搜索框内输入框的 place 参数:x 让出半个画布高,纵向让出一个留白。"""
    _h = int(search_canvas["height"])
    return dict(x=_h // 2, y=_h // SEARCHBOX_PAD_DIV, relwidth=relwidth, relheight=1)


__all__ = ["CONTENT_X_DIV", "CONTENT_Y_DIV", "CONTENT_EDGE",
           "RELAYOUT_HOME", "RELAYOUT_WIDE",
           "content_frame_size", "screen_content_frame_size", "content_place",
           "place_content", "bind_content_resize", "new_content_frame",
           "NAV_WIDTH_DIV", "NAV_HEIGHT_DIV", "NAV_FONT_DIV", "NAV_RELY_DIV",
           "NAV_RELHEIGHT", "NAV_ITEM_RELY", "nav_font", "nav_place_kw", "nav_item_size",
           "scaled_font", "title_item_y", "title_center_y", "control_pad",
           "searchbox_width", "searchbox_height", "searchbox_metrics",
           "searchbox_cover_x", "searchbox_text_pos",
           "input_place_kw", "SEARCHBOX_RELX",
           "SEARCHBOX_WIDTH_DIV", "SEARCHBOX_HEIGHT_DIV", "SEARCHBOX_PAD_DIV",
           "SEARCHBOX_RADIUS_DIV", "SEARCHBOX_BUTTON_DIV", "SEARCHBOX_COVER_MUL",
           "TITLE_CONTROL_OFFSET", "CONTROL_RELX",
           "CONTROL_FONT_DIV_MENU", "CONTROL_FONT_DIV_MINIMIZE",
           "CONTROL_FONT_DIV_MAXIMIZE", "CONTROL_FONT_DIV_CLOSE",
           "INPUT_RELWIDTH_NORMAL", "INPUT_RELWIDTH_MAXIMIZED",
           "TITLE_BAR_WIDTH_DIV", "TITLE_BAR_HEIGHT_DIV",
           "TITLE_LOGO_WIDTH_DIV", "TITLE_LOGO_HEIGHT_DIV",
           "TITLE_LOGO_FONT_DIV", "TITLE_LOGO_IMAGE_DIV",
           "title_bar_width", "title_bar_height", "title_logo_size",
           "title_logo_font", "title_logo_image_size"]
