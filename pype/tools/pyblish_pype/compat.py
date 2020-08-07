import os


def __windows_taskbar_compat():
    """Enable icon and taskbar grouping for Windows 7+"""

    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        u"pyblish_pype")


def init():
    if os.name == "nt":
        __windows_taskbar_compat()
