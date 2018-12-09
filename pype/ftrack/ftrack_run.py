import sys
import os
import argparse
import subprocess
import threading
import time
from app import style
from app.vendor.Qt import QtCore, QtGui, QtWidgets
from pype.ftrack import credentials, login_dialog as login_dialog

from FtrackServer import FtrackServer

from pype import api as pype


# load data from templates
pype.load_data_from_templates()

log = pype.Logger.getLogger(__name__, "ftrack")
# Validation if alredy logged into Ftrack


class FtrackRunner:
    def __init__(self, main_parent=None, parent=None):

        self.parent = parent
        self.loginWidget = login_dialog.Login_Dialog_ui(self)
        self.actionThread = None
        self.actionServer = FtrackServer('action')

        self.boolLogged = False
        self.boolActionServer = False

    def showLoginWidget(self):
        self.loginWidget.show()

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
            else:
                self.showLoginWidget()

        except Exception as e:
            log.error("We are unable to connect to Ftrack: {0}".format(e))

        validation = credentials._check_credentials()
        if validation is True:
            log.info("Connected to Ftrack successfully")
            self.loginChange()
        else:
            log.warning("Please sign in to Ftrack")
            self.boolLogged = False
            self.setMenuVisibility()

        return validation

    # Necessary - login_dialog works with this method after logging in
    def loginChange(self):
        self.boolLogged = True
        self.setMenuVisibility()
        self.runActionServer()

    def logout(self):
        credentials._clear_credentials()
        self.stopActionServer()

        log.info("Logged out of Ftrack")
        self.boolLogged = False
        self.setMenuVisibility()

    # Actions part
    def runActionServer(self):
        if self.actionThread is None:
            self.actionThread = threading.Thread(target=self.setActionServer)
            self.actionThread.daemon = True
            self.actionThread.start()

        log.info("Ftrack action server launched")
        self.boolActionServer = True
        self.setMenuVisibility()

    def setActionServer(self):
        self.actionServer.run_server()

    def resetActionServer(self):
        self.stopActionServer()
        self.runActionServer()

    def stopActionServer(self):
        try:
            self.actionServer.stop_session()
            if self.actionThread is not None:
                self.actionThread.join()
                self.actionThread = None

            log.info("Ftrack action server stopped")
            self.boolActionServer = False
            self.setMenuVisibility()
        except Exception as e:
            log.error("During Killing action server: {0}".format(e))


    # Definition of Tray menu
    def trayMenu(self, parent):
        # Menu for Tray App
        self.menu = QtWidgets.QMenu('Ftrack', parent)
        self.menu.setProperty('submenu', 'on')
        self.menu.setStyleSheet(style.load_stylesheet())

        # Actions - server
        self.smActionS = self.menu.addMenu("Action server")
        self.aRunActionS = QtWidgets.QAction("Run action server", self.smActionS)
        self.aRunActionS.triggered.connect(self.runActionServer)
        self.aResetActionS = QtWidgets.QAction("Reset action server", self.smActionS)
        self.aResetActionS.triggered.connect(self.resetActionServer)
        self.aStopActionS = QtWidgets.QAction("Stop action server", self.smActionS)
        self.aStopActionS.triggered.connect(self.stopActionServer)

        self.smActionS.addAction(self.aRunActionS)
        self.smActionS.addAction(self.aResetActionS)
        self.smActionS.addAction(self.aStopActionS)

        # Actions - basic
        self.aLogin = QtWidgets.QAction("Login", self.menu)
        self.aLogin.triggered.connect(self.validate)
        self.aLogout = QtWidgets.QAction("Logout", self.menu)
        self.aLogout.triggered.connect(self.logout)

        self.menu.addAction(self.aLogin)
        self.menu.addAction(self.aLogout)

        self.boolLogged = False
        self.setMenuVisibility()

        return self.menu

    # Definition of visibility of each menu actions
    def setMenuVisibility(self):

        self.smActionS.menuAction().setVisible(self.boolLogged)
        self.aLogin.setVisible(not self.boolLogged)
        self.aLogout.setVisible(self.boolLogged)

        if self.boolLogged is False:
            return

        self.aRunActionS.setVisible(not self.boolActionServer)
        self.aResetActionS.setVisible(self.boolActionServer)
        self.aStopActionS.setVisible(self.boolActionServer)
