import os
import sys
import textwrap
from app.vendor.Qt import QtCore, QtGui, QtWidgets

menu_layout_dict = {'Ftrack': {
                        'Avalon Core': [
                            'Config core',
                            'Create new project',
                            None,
                            'Save database',
                        ],
                        'Avalon Users': [
                            'Config User',
                            'Cre&ate new user',
                        ],
                        'Avalon Workfiles': [
                            'Config Workfiles',
                        ],
                        'Pyblish': [
                            'Config Pyblish',
                            'Create new micro-plugin',
                            None,
                            'Micro-plugins manager'
                        ],
                        'Pipeline': [
                            'Config pipeline',
                            'Create new template',
                            None,
                            'Templates manager'
                        ],
                        'CG-wire': [
                            'Config CG-wire',
                            None,
                            'Pull database',
                            'Push database'
                        ]
                     },
                    'Minimalize': "action",
                    #'Close': "action"
                    }
# print(menu_layout_dict)
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
        label = QtWidgets.QLabel('Avalon', menu)
        menu.setStyleSheet(textwrap.dedent('''
                                            QWidget {
                                                background-color: #444444;
                                                color: #ffffff;
                                            }
                                            QLineEdit {
                                                    background-color: white;
                                            }
                                             QLineEdit:no-text-inside-it {
                                                    background-color: red;
                                            }
                                            QWidget[menu=on] {
                                                background-color: #333333;
                                                color: #ffffff;
                                            }
                                            '''
                                           )
                           )
        for key, value in menu_layout_dict.items():
             if value == 'action':
                # menu = QtWidgets.QMenu(menu)
                # menu = QtWidgets.QMenu(menu)
                separator = menu.addSeparator()
                # spacer = QtWidgets.QWidget()
                menu.addAction(key)
                print(key, value)
             else:
                # menu = QtWidgets.QMenu(menu)
                avalon_plugins = menu.addMenu(key)
                avalon_plugins.setProperty('submenu', 'on')
                self.eventFilter(avalon_plugins, QtCore.QEvent.HoverMove)
                for skey, svalue in value.items():
                    avalon_plugin = avalon_plugins.addMenu(skey)
                    avalon_plugin.setProperty('submenu', 'on')
                    # print(skey, svalue)
                    # plugins_Menu = avalon_plugin.addMenu(skey)
                    for action in svalue:
                        if action == None:
                            avalon_plugin.addSeparator()
                        else:
                            plugins_Action = avalon_plugin.addAction(action)
                menu.addMenu(avalon_plugins)
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
            print("C'mon! CLick-meeee!!!")
            return True
     def exit(self):
        QtCore.QCoreApplication.exit()

def _sys_tray(image):
    # code source: https://stackoverflow.com/questions/893984/pyqt-show-menu-in-a-system-tray-application  - add answer PyQt5
    #PyQt4 to PyQt5 version: https://stackoverflow.com/questions/20749819/pyqt5-failing-import-of-qtgui
    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QWidget()
    trayIcon = SystemTrayIcon(QtGui.QIcon(image), w)
    # menu =
    trayIcon.show()
    sys.exit(app.exec_())

if (__name__ == ('__main__')):
    avalon_core_icon = r'C:\Users\jakub.trllo\CODE\pype-setup\repos\avalon-launcher\launcher\res\icon\main.png'
    print(avalon_core_icon)
    _sys_tray(avalon_core_icon)
