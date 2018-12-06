import sys
import os
import argparse
import subprocess
import threading
import time
import ftrack_api
from app import style
from app.vendor.Qt import QtCore, QtGui, QtWidgets
from pype.ftrack import credentials, login_dialog as login_dialog

from pype.vendor.pynput import mouse, keyboard
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
        self.eventThread = None
        self.eventServer = FtrackServer('event')
        self.timerThread = None
        self.timerCoundownThread = None

        self.boolLogged = False
        self.boolActionServer = False
        self.boolEventServer = False
        self.boolTimerEvent = False

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
        self.stopEventServer()

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

    # Events part
    def runEventServer(self):
        if self.eventThread is None:
            self.eventThread = threading.Thread(target=self.setEventServer)
            self.eventThread.daemon = True
            self.eventThread.start()

        log.info("Ftrack event server launched")
        self.boolEventServer = True
        self.setMenuVisibility()

    def setEventServer(self):
        self.eventServer.run_server()

    def resetEventServer(self):
        self.stopEventServer()
        self.runEventServer()

    def stopEventServer(self):
        try:
            self.eventServer.stop_session()
            if self.eventThread is not None:
                self.eventThread.join()
                self.eventThread = None

            log.info("Ftrack event server stopped")
            self.boolEventServer = False
            self.setMenuVisibility()
        except Exception as e:
            log.error("During Killing Event server: {0}".format(e))

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

        # Actions - server
        self.smEventS = self.menu.addMenu("Event server")
        self.aRunEventS = QtWidgets.QAction("Run event server", self.smEventS)
        self.aRunEventS.triggered.connect(self.runEventServer)
        self.aResetEventS = QtWidgets.QAction("Reset event server", self.smEventS)
        self.aResetEventS.triggered.connect(self.resetEventServer)
        self.aStopEventS = QtWidgets.QAction("Stop event server", self.smEventS)
        self.aStopEventS.triggered.connect(self.stopEventServer)

        self.smEventS.addAction(self.aRunEventS)
        self.smEventS.addAction(self.aResetEventS)
        self.smEventS.addAction(self.aStopEventS)

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

    def timerEvent(self):
        cred = credentials._get_credentials()
        username = cred['username']
        self.boolTimerEvent = True
        self.timerSession = ftrack_api.Session()
        self.timerSession.event_hub.subscribe(
            'topic=ftrack.update and source.user.username={}'.format(username),
            self.eventHandler)
        # keep event_hub on session running
        self.timerSession.event_hub.wait()

    def timerCountdown(self):
        self.time_left_int = 3
        self.my_qtimer = QtCore.QTimer()
        self.my_qtimer.timeout.connect(self.timer_timeout)
        self.my_qtimer.start(1000)

        if self.time_left_int < 31:
            self.update_gui()

    def timer_timeout(self):
        self.time_left_int -= 1

        if self.time_left_int == 0:
            self.widget_counter_int = (self.widget_counter_int + 1) % 4
            self.pages_qsw.setCurrentIndex(self.widget_counter_int)
            self.time_left_int = DURATION_INT
        if self.time_left_int < 31:
            self.update_gui()

    def update_gui(self):
        txt = "Continue ({})".format(self.time_left_int)
        self.parent.ftrackTimer.btnContinue.setText(txt)

    def runTimerThread(self):
        if self.timerThread is None:
            self.timerThread = threading.Thread(target=self.timerEvent)
            self.timerThread.daemon = True
            self.timerThread.start()
        if self.timerCoundownThread is None:
            self.timerCoundownThread = threading.Thread(target=self.timerCountdown)
            self.timerCoundownThread.daemon = True
            self.timerCoundownThread.start()

    def stopTimerThread(self):
        try:
            self.timerThread.stop_session()
            if self.timerThread is not None:
                self.timerThread.join()
                self.timerThread = None
            self.timerCoundownThread.stop_session()
            if self.timerCoundownThread is not None:
                self.timerCoundownThread.join()
                self.timerCoundownThread = None
            log.info("Timer event server stopped")
            self.boolTimerEvent = False
        except Exception as e:
            log.error("During Killing Timer event server: {0}".format(e))

    def eventHandler(self, event):
        try:
            if event['data']['entities'][0]['objectTypeId'] != 'timer':
                return
        except:
            return
        new = event['data']['entities'][0]['changes']['start']['new']
        old = event['data']['entities'][0]['changes']['start']['old']
        if old is None and new is None:
            return
        elif old is None:
            self.timerStart()
        elif new is None:
            self.timerStop()

    def timerStart(self):
        self.parent.ftrackTimer.show()

    def timerStop(self):
        print("timer has stopped!")

    # Definition of visibility of each menu actions
    def setMenuVisibility(self):

        self.smActionS.menuAction().setVisible(self.boolLogged)
        self.smEventS.menuAction().setVisible(self.boolLogged)
        self.aLogin.setVisible(not self.boolLogged)
        self.aLogout.setVisible(self.boolLogged)

        if self.boolLogged is False:
            if self.boolTimerEvent is True:
                self.stopTimerThread()
            return

        self.aRunActionS.setVisible(not self.boolActionServer)
        self.aResetActionS.setVisible(self.boolActionServer)
        self.aStopActionS.setVisible(self.boolActionServer)

        if self.boolTimerEvent is False:
            self.runTimerThread()
        self.aRunEventS.setVisible(not self.boolEventServer)
        self.aResetEventS.setVisible(self.boolEventServer)
        self.aStopEventS.setVisible(self.boolEventServer)

class StopTimer(QtWidgets.QWidget):

    SIZE_W = 300
    SIZE_H = 230

    def __init__(self, parent=None):

        super(StopTimer, self).__init__()

        self.parent = parent
        self.msg = """ You didn't work for a long time.
        Would you like to stop Ftrack timer?
        """
        # self.setWindowIcon(self.parent.parent.icon)
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMinimizeButtonHint)

        self._translate = QtCore.QCoreApplication.translate

        self.font = QtGui.QFont()
        self.font.setFamily("DejaVu Sans Condensed")
        self.font.setPointSize(9)
        self.font.setBold(True)
        self.font.setWeight(50)
        self.font.setKerning(True)

        self.resize(self.SIZE_W, self.SIZE_H)
        self.setMinimumSize(QtCore.QSize(self.SIZE_W, self.SIZE_H))
        self.setMaximumSize(QtCore.QSize(self.SIZE_W+100, self.SIZE_H+100))
        self.setStyleSheet(style.load_stylesheet())

        self.setLayout(self._main())
        self.setWindowTitle('Pype - Stop Ftrack timer')

    def _main(self):
        self.main = QtWidgets.QVBoxLayout()
        self.main.setObjectName("main")

        self.form = QtWidgets.QFormLayout()
        self.form.setContentsMargins(10, 15, 10, 5)
        self.form.setObjectName("form")

        self.info_label = QtWidgets.QLabel(self.msg)
        self.info_label.setFont(self.font)
        self.info_label.setTextFormat(QtCore.Qt.RichText)
        self.info_label.setObjectName("info_label")
        self.info_label.setWordWrap(True);

        self.form.addRow(self.info_label)

        self.btnGroup = QtWidgets.QHBoxLayout()
        self.btnGroup.addStretch(1)
        self.btnGroup.setObjectName("btnGroup")

        self.btnStop = QtWidgets.QPushButton("Stop timer")
        self.btnStop.setToolTip('Stop\'s Ftrack timer')
        self.btnStop.clicked.connect(self.stop_timer)

        self.btnContinue = QtWidgets.QPushButton("Continue")
        self.btnContinue.setToolTip('Timer will continue')
        self.btnContinue.clicked.connect(self.close_widget)

        self.btnGroup.addWidget(self.btnContinue)
        self.btnGroup.addWidget(self.btnStop)

        self.main.addLayout(self.form)
        self.main.addLayout(self.btnGroup)

        return self.main

    def stop_timer(self):
        print("now i should stop the timer")
    def close_widget(self):
        self.close()
