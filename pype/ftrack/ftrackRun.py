import sys
import os
import argparse
import subprocess
import threading
import time
from app import style
from app.vendor.Qt import QtCore, QtGui, QtWidgets
from pype.ftrack import credentials, login_dialog as login_dialog

# Validation if alredy logged into Ftrack
class FtrackRunner:
    def __init__(self, parent=None):
        self.parent = parent
        self.parent.loginWidget = login_dialog.Login_Dialog_ui()

        # try:
        #     self.validate()
        # except Exception as e:
        #     print(e)

        # self.setServer()
        self.validate()

    def showLoginWidget(self):
        # self.parent.loginWidget.exec_()

        # self.parent.loginWidget.show()
        # self.parent.loginWidget.showMe()
        test = login_dialog.Login_Dialog_ui()
        test.show()
        del(test)


    def validate(self):
        validation = False
        cred = credentials._get_credentials()
        try:
            if 'username' in cred and 'apiKey' in cred:
                validation = credentials._check_credentials(
                    cred['username'],
                    cred['apiKey']
                )
                if validation is False:
                    self.showLoginWidget()
                    # login_dialog.run_login()
            else:
                self.showLoginWidget()
                # login_dialog.run_login()

        except Exception as e:
            print(e)

        validation = credentials._check_credentials()
        if not validation:
            print("We are unable to connect to Ftrack")
            sys.exit()

    def logout(self):
        credentials._clear_credentials()
        print("Logged out of Ftrack")

    def trayMenu(self, parent):
        # Menu for Tray App
        menu = QtWidgets.QMenu('Ftrack', parent)
        menu.setProperty('submenu', 'on')
        menu.setStyleSheet(style.load_stylesheet())

        # Actions - server
        smActionS = menu.addMenu("Servers")
        aRunActionS = QtWidgets.QAction("Run action server", smActionS)
        aRunActionS.triggered.connect(self.runServer)
        aStopActionS = QtWidgets.QAction("Stop action server", smActionS)
        aStopActionS.triggered.connect(self.stopServer)

        smActionS.addAction(aRunActionS)
        smActionS.addAction(aStopActionS)

        # Actions - basic
        aLogin = QtWidgets.QAction("Login",menu)
        aLogin.triggered.connect(self.validate)
        aLogout = QtWidgets.QAction("Logout",menu)
        aLogout.triggered.connect(self.logout)

        menu.addAction(aLogin)
        menu.addAction(aLogout)

        return menu

    def setServer(self):
        fname = os.path.join(os.environ["FTRACK_ACTION_SERVER"], "actionServer.py")
        print(fname)
        DETACHED_PROCESS = 0x00000008
        self.aServer = subprocess.Popen(
            [fname],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            cwd=None,
            env=os.environ,
            executable=sys.executable,
            creationflags=DETACHED_PROCESS
        )

    def runServer(self):
        print("Running server")
        self.aServer.wait()

    def stopServer(self):
        print("Stopping server")
        self.aServer.close()
