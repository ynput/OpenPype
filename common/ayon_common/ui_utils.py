import sys
from qtpy import QtWidgets, QtCore


def set_style_property(widget, property_name, property_value):
    """Set widget's property that may affect style.

    Style of widget is polished if current property value is different.
    """

    cur_value = widget.property(property_name)
    if cur_value == property_value:
        return
    widget.setProperty(property_name, property_value)
    widget.style().polish(widget)


def get_qt_app():
    app = QtWidgets.QApplication.instance()
    if app is not None:
        return app

    for attr_name in (
        "AA_EnableHighDpiScaling",
        "AA_UseHighDpiPixmaps",
    ):
        attr = getattr(QtCore.Qt, attr_name, None)
        if attr is not None:
            QtWidgets.QApplication.setAttribute(attr)

    if hasattr(QtWidgets.QApplication, "setHighDpiScaleFactorRoundingPolicy"):
        QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(
            QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    return QtWidgets.QApplication(sys.argv)
