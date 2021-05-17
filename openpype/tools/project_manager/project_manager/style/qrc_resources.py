import Qt


initialized = False
resources = None
if Qt.__binding__ == "PySide2":
    from . import pyside2_resources as resources
elif Qt.__binding__ == "PyQt5":
    from . import pyqt5_resources as resources


def qInitResources():
    global resources
    global initialized
    if resources is not None and not initialized:
        initialized = True
        resources.qInitResources()


def qCleanupResources():
    global resources
    global initialized
    if resources is not None:
        initialized = False
        resources.qCleanupResources()
