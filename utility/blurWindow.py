# -*- coding: utf-8 -*-
"""毛玻璃(BlurBehind/Acrylic)窗口特效 —— vendored 自 Peticali/PythonBlurBehind

上游: https://github.com/Peticali/PythonBlurBehind  (blurWindow/blurWindow.py, BlurWindow 1.2.1)
本项目改动:剥离全部 PyQt5 依赖 ——
    1. Windows/Linux 核心路径本来就只靠 ctypes,原样保留;
    2. macOS 的 MacBlur 原来用 PyQt5 的 QMacCocoaViewContainer 承载 NSVisualEffectView,
       改为纯 pyobjc 直接挂到 NSView 所在 NSWindow 的 contentView 下(本项目以 Windows 为主,此分支未实测);
    3. 上游 __main__ 的 PyQt5 演示换成 tkinter 演示(python utility/blurWindow.py 直接看效果);
    4. 加了 tk_hwnd():tkinter 拿顶层 HWND 的助手(毛玻璃必须打在顶层窗口上,见下)。

用法(Windows + tkinter):
    import blurWindow
    hwnd = blurWindow.tk_hwnd(root)
    blurWindow.GlobalBlur(hwnd, Acrylic=True, Dark=True, hexColor='#20202080')
    hexColor 是 #RRGGBBAA(注意 AA 在末尾,与 CSS 相反);不传则由系统出纯模糊。

关键坑:毛玻璃只在窗口"有透明像素"的地方透出来。tkinter 想看到效果必须配合
    root.wm_attributes("-transparent", 色键颜色)  把背景做成透明;
    而本项目 chrome.py 已因"色键区域鼠标穿透"弃用色键 —— 接入前先解决透明区域命中测试,
    或者只在局部(如侧栏)用色键,别全窗口铺。
"""
import platform
import ctypes

if platform.system() == 'Darwin':
    from AppKit import *

    def MacBlur(NSView, Material=NSVisualEffectMaterialPopover, TitleBar: bool = True):
        """原签名收 QWidget 并借 PyQt5 挂视图;现直接收 NSView(tk 的 cocoa 视图可经 winId 取得)。"""
        view = objc.objc_object(c_void_p=NSView.winId().__int__())

        visualEffectView = NSVisualEffectView.new()
        visualEffectView.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)  # window resizable
        visualEffectView.setFrame_(NSMakeRect(0, 0, NSView.width(), NSView.height()))
        visualEffectView.setState_(NSVisualEffectStateActive)
        visualEffectView.setMaterial_(Material)  # https://developer.apple.com/documentation/appkit/nsvisualeffectmaterial
        visualEffectView.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)

        window = view.window()
        content = window.contentView()
        # 垫到内容视图最底层:NSWindowBelow=-1,相对锚点用 tk 自己的视图
        content.addSubview_positioned_relativeTo_(visualEffectView, NSWindowBelow, view)

        if TitleBar:
            # TitleBar with blur
            window.setTitlebarAppearsTransparent_(True)
            window.setStyleMask_(window.styleMask() | NSFullSizeContentViewWindowMask)


if platform.system() == 'Windows':
    from ctypes.wintypes import DWORD, BOOL, HRGN, HWND
    user32 = ctypes.windll.user32
    dwm = ctypes.windll.dwmapi

    class ACCENTPOLICY(ctypes.Structure):
        _fields_ = [
            ("AccentState", ctypes.c_uint),
            ("AccentFlags", ctypes.c_uint),
            ("GradientColor", ctypes.c_uint),
            ("AnimationId", ctypes.c_uint)
        ]

    class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
        _fields_ = [
            ("Attribute", ctypes.c_int),
            ("Data", ctypes.POINTER(ctypes.c_int)),
            ("SizeOfData", ctypes.c_size_t)
        ]

    class DWM_BLURBEHIND(ctypes.Structure):
        _fields_ = [
            ('dwFlags', DWORD),
            ('fEnable', BOOL),
            ('hRgnBlur', HRGN),
            ('fTransitionOnMaximized', BOOL)
        ]

    class MARGINS(ctypes.Structure):
        _fields_ = [("cxLeftWidth", ctypes.c_int),
                    ("cxRightWidth", ctypes.c_int),
                    ("cyTopHeight", ctypes.c_int),
                    ("cyBottomHeight", ctypes.c_int)
                    ]

    SetWindowCompositionAttribute = user32.SetWindowCompositionAttribute
    SetWindowCompositionAttribute.argtypes = (HWND, WINDOWCOMPOSITIONATTRIBDATA)
    SetWindowCompositionAttribute.restype = ctypes.c_int


def tk_hwnd(widget):
    """tkinter 部件 -> 顶层窗口 HWND。

    winfo_id() 给到的是 Tk 内层子窗口(TkChild),SetWindowCompositionAttribute/DWM
    要打在它的父窗口(顶层 frame)上才可靠;本模块 Windows 路径统一经它取句柄。
    """
    return user32.GetParent(widget.winfo_id())


def ExtendFrameIntoClientArea(HWND):
    margins = MARGINS(-1, -1, -1, -1)
    dwm.DwmExtendFrameIntoClientArea(HWND, ctypes.byref(margins))


def Win7Blur(HWND, Acrylic):
    if Acrylic == False:
        DWM_BB_ENABLE = 0x01
        bb = DWM_BLURBEHIND()
        bb.dwFlags = DWM_BB_ENABLE
        bb.fEnable = 1
        bb.hRgnBlur = 1
        dwm.DwmEnableBlurBehindWindow(HWND, ctypes.byref(bb))
    else:
        ExtendFrameIntoClientArea(HWND)


def HEXtoRGBAint(HEX: str):
    alpha = HEX[7:]
    blue = HEX[5:7]
    green = HEX[3:5]
    red = HEX[1:3]

    gradientColor = alpha + blue + green + red
    return int(gradientColor, base=16)


def blur(hwnd, hexColor=False, Acrylic=False, Dark=False):
    accent = ACCENTPOLICY()
    accent.AccentState = 3  # Default window Blur #ACCENT_ENABLE_BLURBEHIND

    gradientColor = 0

    if hexColor != False:
        gradientColor = HEXtoRGBAint(hexColor)
        accent.AccentFlags = 2  # Window Blur With Accent Color #ACCENT_ENABLE_TRANSPARENTGRADIENT

    if Acrylic:
        accent.AccentState = 4  # UWP but LAG #ACCENT_ENABLE_ACRYLICBLURBEHIND
        if hexColor == False:  # UWP without color is translucent
            accent.AccentFlags = 2
            gradientColor = HEXtoRGBAint('#12121240')  # placeholder color

    accent.GradientColor = gradientColor

    data = WINDOWCOMPOSITIONATTRIBDATA()
    data.Attribute = 19  # WCA_ACCENT_POLICY
    data.SizeOfData = ctypes.sizeof(accent)
    data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.POINTER(ctypes.c_int))

    SetWindowCompositionAttribute(int(hwnd), data)

    if Dark:
        data.Attribute = 26  # WCA_USEDARKMODECOLORS
        SetWindowCompositionAttribute(int(hwnd), data)


def BlurLinux(WID):  # may not work in all distros (working in Deepin)
    import os

    c = "xprop -f _KDE_NET_WM_BLUR_BEHIND_REGION 32c -set _KDE_NET_WM_BLUR_BEHIND_REGION 0 -id " + str(WID)
    os.system(c)


def GlobalBlur(HWND, hexColor=False, Acrylic=False, Dark=False, widget=None):
    release = platform.release()
    system = platform.system()

    if system == 'Windows':
        if release == 'Vista':
            Win7Blur(HWND, Acrylic)
        else:
            release = int(float(release))
            if release == 10 or release == 8 or release == 11:  # idk what windows 8.1 spits, if is '8.1' int(float(release)) will work...
                blur(HWND, hexColor, Acrylic, Dark)
            else:
                Win7Blur(HWND, Acrylic)

    if system == 'Linux':
        BlurLinux(HWND)

    if system == 'Darwin':
        MacBlur(widget)


if __name__ == '__main__':
    # 原 __main__ 是 PyQt5 演示,这里换成 tkinter(本项目同款技术栈),兼当冒烟测试
    from tkinter import Tk, Label

    root = Tk()
    root.config(bg='green')
    root.wm_attributes("-transparent", 'green')  # 色键区域透明,毛玻璃从这里透出来
    root.geometry('500x400')
    root.update()

    GlobalBlur(tk_hwnd(root), Acrylic=True, Dark=True)

    Label(root, text='Can you see me?', bg='green', fg='white',
          font=('Microsoft YaHei UI', 14)).pack(expand=True)

    root.mainloop()
