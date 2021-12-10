from __future__ import print_function

import os
import sys
import ctypes
import platform
import contextlib

from . import control, settings, util, window
from Qt import QtCore, QtGui, QtWidgets

self = sys.modules[__name__]

# Maintain reference to currently opened window
self._window = None


@contextlib.contextmanager
def application():
    app = QtWidgets.QApplication.instance()

    if not app:
        print("Starting new QApplication..")
        app = QtWidgets.QApplication(sys.argv)
        yield app
        app.exec_()
    else:
        print("Using existing QApplication..")
        yield app
        if os.environ.get("PYBLISH_GUI_ALWAYS_EXEC"):
            app.exec_()


def install_translator(app):
    translator = QtCore.QTranslator(app)
    translator.load(QtCore.QLocale.system(), "i18n/",
                    directory=util.root)
    app.installTranslator(translator)
    print("Installed translator")


def install_fonts():
    database = QtGui.QFontDatabase()
    fonts = [
        "opensans/OpenSans-Bold.ttf",
        "opensans/OpenSans-BoldItalic.ttf",
        "opensans/OpenSans-ExtraBold.ttf",
        "opensans/OpenSans-ExtraBoldItalic.ttf",
        "opensans/OpenSans-Italic.ttf",
        "opensans/OpenSans-Light.ttf",
        "opensans/OpenSans-LightItalic.ttf",
        "opensans/OpenSans-Regular.ttf",
        "opensans/OpenSans-Semibold.ttf",
        "opensans/OpenSans-SemiboldItalic.ttf",
        "fontawesome/fontawesome-webfont.ttf"
    ]

    for font in fonts:
        path = util.get_asset("font", font)

        # TODO(marcus): Check if they are already installed first.
        # In hosts, this will be called each time the GUI is shown,
        # potentially installing a font each time.
        if database.addApplicationFont(path) < 0:
            print("Could not install %s\n" % path)
        else:
            print("Installed %s\n" % font)


def on_destroyed():
    """Remove internal reference to window on window destroyed"""
    self._window = None


def show(parent=None):
    with open(util.get_asset("app.css")) as f:
        css = f.read()

        # Make relative paths absolute
        root = util.get_asset("").replace("\\", "/")
        css = css.replace("url(\"", "url(\"%s" % root)

    with application() as app:

        if platform.system().lower() == "windows":
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                u"pyblish_pype"
            )

        install_fonts()
        install_translator(app)

        ctrl = control.Controller()

        if self._window is None:
            self._window = window.Window(ctrl, parent)
            self._window.destroyed.connect(on_destroyed)

        self._window.show()
        self._window.activateWindow()
        env_title = os.getenv("PYBLISH_TITLE")
        if env_title:
            self._window.setWindowTitle(env_title)
        else:
            self._window.setWindowTitle(settings.WindowTitle)

        font = QtGui.QFont("Open Sans", 8, QtGui.QFont.Normal)
        self._window.setFont(font)
        self._window.setStyleSheet(css)

        self._window.reset()
        self._window.resize(*settings.WindowSize)

        return self._window
