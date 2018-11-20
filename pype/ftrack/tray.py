import os
import sys
import textwrap
from pype.ftrack.ftrackRun import FtrackRunner
from app import style
from app.vendor.Qt import QtCore, QtGui, QtWidgets


class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        QtWidgets.QSystemTrayIcon.__init__(self, icon, parent)

        self.parent = parent
        self.tray = QtWidgets.QSystemTrayIcon(icon, parent)
        self.tray.setToolTip("Avalon Launcher")

        self.menu = QtWidgets.QMenu(self.parent)
        self.menu.setStyleSheet(style.load_stylesheet())

        # TODO - Recognize that ftrack is used:
        self.ftrack = FtrackRunner()
        self.menu.addMenu(self.ftrack.trayMenu(self.menu))

        aExit = QtWidgets.QAction("Exit", self)
        aExit.triggered.connect(self.exit)
        self.menu.addAction(aExit)

        self.setContextMenu(self.menu)

    def eventFilter(self, object, event):
        print(self, object, event)
        if event.type() == QtCore.QEvent.MouseButtonPress:
            print("You pressed the button")
            return True

        if event == QtCore.QEvent.HoverMove:
            return True

    def exit(self):
        QtCore.QCoreApplication.exit()

def _sys_tray(image):
    # code source: https://stackoverflow.com/questions/893984/pyqt-show-menu-in-a-system-tray-application  - add answer PyQt5
    #PyQt4 to PyQt5 version: https://stackoverflow.com/questions/20749819/pyqt5-failing-import-of-qtgui
    # app = QtWidgets.QApplication(sys.argv)
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(True)
    w = QtWidgets.QWidget()
    trayIcon = SystemTrayIcon(QtGui.QIcon(image), w)
    trayIcon.show()
    sys.exit(app.exec_())

if (__name__ == ('__main__')):
    avalon_core_icon = r'C:\Users\jakub.trllo\CODE\pype-setup\repos\avalon-launcher\launcher\res\icon\main.png'
    _sys_tray(avalon_core_icon)
