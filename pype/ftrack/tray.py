import os
import sys
import textwrap
from pype.ftrack.ftrackRun import FtrackRunner, login_dialog
from app import style
from app.vendor.Qt import QtCore, QtGui, QtWidgets


class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    def __init__(self, parent=None):

        icon = r'C:\Users\jakub.trllo\CODE\pype-setup\repos\avalon-launcher\launcher\res\icon\main.png'
        icon = QtGui.QIcon(icon)

        QtWidgets.QSystemTrayIcon.__init__(self, icon, parent)

        # Store parent - QtWidgets.QMainWindow()
        self.parent = parent

        # Setup menu in Tray
        self.menu = QtWidgets.QMenu()
        self.menu.setStyleSheet(style.load_stylesheet())

        # Add ftrack menu (TODO - Recognize that ftrack is used!!!!!!)
        self.ftrack = FtrackRunner(self.parent, self)
        self.menu.addMenu(self.ftrack.trayMenu(self.menu))

        # Add Exit action to menu
        aExit = QtWidgets.QAction("Exit", self)
        aExit.triggered.connect(self.exit)
        self.menu.addAction(aExit)

        # Add menu to Context of SystemTrayIcon
        self.setContextMenu(self.menu)

    def exit(self):
        QtCore.QCoreApplication.exit()


def _sys_tray():
    # code source: https://stackoverflow.com/questions/893984/pyqt-show-menu-in-a-system-tray-application  - add answer PyQt5
    #PyQt4 to PyQt5 version: https://stackoverflow.com/questions/20749819/pyqt5-failing-import-of-qtgui
    app = QtWidgets.QApplication(sys.argv)
    # app.setQuitOnLastWindowClosed(True)
    w = QtWidgets.QMainWindow()
    # w = QtWidgets.QWidget()
    trayIcon = SystemTrayIcon(w)
    trayIcon.show()
    sys.exit(app.exec_())

if (__name__ == ('__main__')):
    _sys_tray()
