import qtpy


initialized = False
resources = None
if qtpy.API == "pyside6":
    from . import pyside6_resources as resources
elif qtpy.API == "pyside2":
    from . import pyside2_resources as resources
elif qtpy.API == "pyqt5":
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


__all__ = (
    "resources",
    "qInitResources",
    "qCleanupResources"
)
