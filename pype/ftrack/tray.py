import os
import sys
import textwrap
from app import style
from app.vendor.Qt import QtCore, QtGui, QtWidgets

ftrack_layout = {
    'Avalon Users': {
        'Config User',
        'Cre&ate new user',
     },
    'Avalon Workfiles': {
        'Config Workfiles',
    },
    'Pyblish': {
        'Config Pyblish',
        'Create new micro-plugin',
        None,
        'Micro-plugins manager'
    },
    'Pipeline': {
        'Config pipeline',
        'Create new template',
        None,
        'Templates manager'
    },
    'Logout': "action",
}
applications = {
    'app_one':'action',
    'app_two':'action'
}

menu_layout_dict = {'Ftrack':ftrack_layout, 'Apps':applications}

class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
     def __init__(self, icon, parent=None):
        QtWidgets.QSystemTrayIcon.__init__(self, icon, parent)
        self.tray = QtWidgets.QSystemTrayIcon(icon, parent)
        # print(tray)
        self.tray.setToolTip("Avalon Launcher")
        menu = QtWidgets.QMenu(parent)
        # self.menuBar()
        # self.main_layout = QtWidgets.QVBoxLayout(self.menu)
        # self.menu.setLayout(self.main_layout)
        # project_name_lbl = QtWidgets.QLabel('<b>Project Name</b>')
        # self.main_layout.addWidget(project_name_lbl)
        menu.setProperty('menu', 'on')

        menu.setStyleSheet(style.load_stylesheet())
        for key, value in menu_layout_dict.items():
            print(100*"*")
            print(key)
            print(value)
            if value == 'action':
                separator = menu.addSeparator()
                # spacer = QtWidgets.QWidget()
                menu.addAction(key)
            else:
                # menu = QtWidgets.QMenu(menu)
                combo_box = menu.addMenu(key)
                combo_box.setProperty('submenu', 'on')
                self.eventFilter(combo_box, QtCore.QEvent.HoverMove)
                for skey, svalue in value.items():
                    if svalue == 'action':
                        combo_box.addAction(skey)
                    elif svalue is None:
                        combo_box.addSeparator()
                    else:
                        nextbox = combo_box.addMenu(skey)
                        nextbox.setProperty('submenu', 'on')
                        for action in svalue:
                            if action == None:
                                nextbox.addSeparator()
                            else:
                                nextbox.addAction(action)
                menu.addMenu(combo_box)

        exitAction = menu.addAction("Exit")

        self.eventFilter(exitAction, QtCore.QEvent.HoverMove)
        self.setContextMenu(menu)
        menu.triggered.connect(self.exit)
         # main_layout.addWidget(menu)
     def eventFilter(self, object, event):
        print(self, object, event)
        # if event.type() == QtCore.QEvent.MouseButtonPress:
        #     print("You pressed the button")
        #     return True
        # #
        if event == QtCore.QEvent.HoverMove:
            return True
     def exit(self):
        QtCore.QCoreApplication.exit()

def _sys_tray(image):
    # code source: https://stackoverflow.com/questions/893984/pyqt-show-menu-in-a-system-tray-application  - add answer PyQt5
    #PyQt4 to PyQt5 version: https://stackoverflow.com/questions/20749819/pyqt5-failing-import-of-qtgui
    # app = QtWidgets.QApplication(sys.argv)
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    w = QtWidgets.QWidget()
    trayIcon = SystemTrayIcon(QtGui.QIcon(image), w)
    # menu =
    trayIcon.show()
    sys.exit(app.exec_())

if (__name__ == ('__main__')):
    avalon_core_icon = r'C:\Users\jakub.trllo\CODE\pype-setup\repos\avalon-launcher\launcher\res\icon\main.png'
    _sys_tray(avalon_core_icon)
