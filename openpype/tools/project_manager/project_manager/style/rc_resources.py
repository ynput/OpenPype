import Qt


resources = None
if Qt.__binding__ == "PySide2":
    from . import pyside2_resources as resources
elif Qt.__binding__ == "PyQt5":
    from . import pyqt5_resources as resources


if resources is not None:
    resources.qInitResources()
