# -*- coding: utf-8 -*-
"""程序图标工具类 —— 一个大类单独成模块

App_icon:窗口 / 任务栏 / 程序坞 图标的唯一入口。

    App_icon.use_process_identity()   进程级任务栏身份(Windows AppUserModelID),建窗口前调一次
    App_icon.apply_default(window)    主窗口:自己带图标,之后新建的 Toplevel 也自动继承
    App_icon.apply(window)            普通窗口:标题栏 + 任务栏
    App_icon.reapply(window)          窗口重新映射后再刷一次(图标句柄复用,可放心重复调)
    App_icon.path()                   图标文件路径(ico/logo.ico,只读资源,与程序同目录)
    App_icon.image()                  读成 PIL 图片,给界面里画 logo 用

Windows 上任务栏图标要三件事一起做,少一件就会退回 Tk 默认的羽毛图标:
    1. SetCurrentProcessExplicitAppUserModelID  不设则任务栏把程序归到 python.exe 名下并沿用它的图标;
    2. WM_SETICON + ICON_BIG(32px)              任务栏 / Alt+Tab 读的是大图标;
    3. WM_SETICON + ICON_SMALL(16px)            标题栏读的是小图标。
Tk 的 wm iconbitmap 在 Windows 上只设小图标,所以大图标必须自己 SendMessage 补上。
mac / linux 走 iconphoto(PIL 读 .ico),引用池防止图片被回收后图标消失。
"""
import os

from PIL import Image

from model.paths import IS_WINDOWS, application_path, windll

ICON_NAME = os.path.join("ico", "logo.ico")   # 程序图标:只读资源,与 videovlc 一起放在 application_path 下
TASKBAR_APP_ID = "VGVideo.Player.1.0"   # 任务栏身份:同一 AUMID 的窗口会被系统归成一组

# ===== Win32 常量与 ctypes 原型 =====
WM_SETICON = 0x0080
ICON_SMALL = 0
ICON_BIG = 1
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010

_win32_ready = False


def _win32():  # 返回配好原型的 user32(GetParent/LoadImageW/SendMessageW);非 Windows 或不可用返回 None
    global _win32_ready
    if not IS_WINDOWS or windll is None:
        return None
    try:
        u32 = windll.user32
        if not _win32_ready:
            from ctypes import c_void_p, c_wchar_p, c_uint, c_int
            # 必须显式声明:指针型返回值默认按 int 截断,64 位下句柄会被砍掉一半
            u32.GetParent.restype = c_void_p
            u32.GetParent.argtypes = [c_void_p]
            u32.LoadImageW.restype = c_void_p
            u32.LoadImageW.argtypes = [c_void_p, c_wchar_p, c_uint, c_int, c_int, c_uint]
            u32.SendMessageW.restype = c_void_p
            u32.SendMessageW.argtypes = [c_void_p, c_uint, c_void_p, c_void_p]
            _win32_ready = True
        return u32
    except Exception:
        return None


class App_icon(object):  # 窗口/任务栏/程序坞图标工具类(全静态,直接用类名调)
    refs = []               # PhotoImage 引用池(mac/linux:不持引用会被 GC,图标随之消失)
    _hicons = {}            # (图标路径, 尺寸) -> HICON:句柄复用,避免重复 LoadImage 泄漏
    _identity_done = False  # 进程身份只设一次

    # ---------------- 路径 / 进程身份 ----------------
    @staticmethod
    def path():  # 图标文件绝对路径(打包后指向 _MEIPASS,源码运行指向项目根)
        return os.path.join(application_path, ICON_NAME)

    @classmethod
    def use_process_identity(cls, app_id=TASKBAR_APP_ID):  # 设进程级任务栏身份;必须早于建窗口
        if cls._identity_done:
            return True
        if not IS_WINDOWS or windll is None:
            return False
        try:
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(str(app_id))
            cls._identity_done = True
            return True
        except Exception:
            return False

    # ---------------- 给窗口设图标 ----------------
    @classmethod
    def apply(cls, window, default=False):  # 设置窗口图标(标题栏+任务栏);default=True 时后续 Toplevel 也继承
        icon = cls.path()
        if not os.path.isfile(icon):
            return False
        try:
            if IS_WINDOWS:
                cls._apply_windows(window, icon, default)
            else:
                cls._apply_photo(window, icon)
            return True
        except Exception:
            return False

    @classmethod
    def apply_default(cls, window):  # 主窗口开局调一次
        return cls.apply(window, default=True)

    @classmethod
    def reapply(cls, window):  # 窗口重新映射(无边框窗口从任务栏还原)后再刷一次
        return cls.apply(window)

    # ---------------- 平台实现 ----------------
    @classmethod
    def _apply_windows(cls, window, icon, default):
        try:  # Tk 接口:管标题栏(小图标),default 顺带设成后续 Toplevel 的默认图标
            window.iconbitmap(icon)
        except Exception:
            pass
        if default:
            try:
                window.iconbitmap(default=icon)
            except Exception:
                pass
        cls._send_icon(window, icon, ICON_BIG, 32)    # 任务栏 / Alt+Tab 认大图标(Tk 不管这块)
        cls._send_icon(window, icon, ICON_SMALL, 16)  # 标题栏认小图标

    @classmethod
    def _send_icon(cls, window, icon, kind, size):
        u32 = _win32()
        if u32 is None:
            return
        try:
            key = (icon, size)
            hicon = cls._hicons.get(key)
            if not hicon:
                hicon = u32.LoadImageW(None, icon, IMAGE_ICON, size, size, LR_LOADFROMFILE)
                if not hicon:
                    return
                cls._hicons[key] = hicon
            hwnd = window.winfo_id()      # Tk 顶层窗口外面还套了一层 wrapper,图标要设在最外层上
            parent = u32.GetParent(hwnd)
            if parent:
                hwnd = parent
            u32.SendMessageW(hwnd, WM_SETICON, kind, hicon)
        except Exception:
            pass

    @classmethod
    def _apply_photo(cls, window, icon):
        try:
            from PIL import ImageTk
            img = ImageTk.PhotoImage(file=icon)
            cls.refs.append(img)
            window.iconphoto(True, img)
        except Exception:
            pass

    # ---------------- 界面里画 logo ----------------
    @staticmethod
    def image():  # 读成 PIL 图片(主窗口左上角那个 logo)
        return Image.open(App_icon.path())


__all__ = ["ICON_NAME", "TASKBAR_APP_ID", "App_icon"]
