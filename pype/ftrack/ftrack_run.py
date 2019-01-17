import os
import json
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


class FtrackRunner:
    def __init__(self, main_parent=None, parent=None):

        self.parent = parent
        self.widget_login = login_dialog.Login_Dialog_ui(self)
        self.widget_timer = StopTimer(self)
        self.action_server = FtrackServer('action')
        self.thread_action_server = None
        self.thread_timer = None
        self.thread_timer_coundown = None

        # self.signal_start_timer.connect(self.timerStart)

        self.bool_logged = False
        self.bool_action_server = False
        self.bool_timer_event = False

    def show_login_widget(self):
        self.widget_login.show()

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
                    self.show_login_widget()
            else:
                self.show_login_widget()

        except Exception as e:
            log.error("We are unable to connect to Ftrack: {0}".format(e))

        validation = credentials._check_credentials()
        if validation is True:
            log.info("Connected to Ftrack successfully")
            self.loginChange()
        else:
            log.warning("Please sign in to Ftrack")
            self.bool_logged = False
            self.set_menu_visibility()

        return validation

    # Necessary - login_dialog works with this method after logging in
    def loginChange(self):
        self.bool_logged = True
        self.set_menu_visibility()
        self.start_action_server()

    def logout(self):
        credentials._clear_credentials()
        self.stop_action_server()

        log.info("Logged out of Ftrack")
        self.bool_logged = False
        self.set_menu_visibility()

    # Actions part
    def start_action_server(self):
        if self.thread_action_server is None:
            self.thread_action_server = threading.Thread(
                target=self.set_action_server
            )
            self.thread_action_server.daemon = True
            self.thread_action_server.start()

        log.info("Ftrack action server launched")
        self.bool_action_server = True
        self.set_menu_visibility()

    def set_action_server(self):
        try:
            self.action_server.run_server()
        except Exception:
            msg = 'Ftrack Action server crashed! Please try to start again.'
            log.error(msg)
            # TODO show message to user
            self.bool_action_server = False
            self.set_menu_visibility()

    def reset_action_server(self):
        self.stop_action_server()
        self.start_action_server()

    def stop_action_server(self):
        try:
            self.action_server.stop_session()
            if self.thread_action_server is not None:
                self.thread_action_server.join()
                self.thread_action_server = None

            log.info("Ftrack action server stopped")
            self.bool_action_server = False
            self.set_menu_visibility()
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

        self.aRunActionS = QtWidgets.QAction(
            "Run action server", self.smActionS
        )
        self.aResetActionS = QtWidgets.QAction(
            "Reset action server", self.smActionS
        )
        self.aStopActionS = QtWidgets.QAction(
            "Stop action server", self.smActionS
        )

        self.aRunActionS.triggered.connect(self.start_action_server)
        self.aResetActionS.triggered.connect(self.reset_action_server)
        self.aStopActionS.triggered.connect(self.stop_action_server)

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

        self.bool_logged = False
        self.set_menu_visibility()

        return self.menu

    # Definition of visibility of each menu actions
    def set_menu_visibility(self):

        self.smActionS.menuAction().setVisible(self.bool_logged)
        self.aLogin.setVisible(not self.bool_logged)
        self.aLogout.setVisible(self.bool_logged)

        if self.bool_logged is False:
            if self.bool_timer_event is True:
                self.stop_timer_thread()
            return

        self.aRunActionS.setVisible(not self.bool_action_server)
        self.aResetActionS.setVisible(self.bool_action_server)
        self.aStopActionS.setVisible(self.bool_action_server)

        if self.bool_timer_event is False:
            self.start_timer_thread()

    def start_timer_thread(self):
        try:
            if self.thread_timer is None:
                self.thread_timer = FtrackEventsThread(self)
                self.bool_timer_event = True
                self.thread_timer.signal_timer_started.connect(
                    self.timer_started
                )
                self.thread_timer.signal_timer_stopped.connect(
                    self.timer_stopped
                )
                self.thread_timer.start()
        except Exception:
            pass

    def stop_timer_thread(self):
        try:
            if self.thread_timer is not None:
                self.thread_timer.terminate()
                self.thread_timer.wait()
                self.thread_timer = None

        except Exception as e:
            log.error("During Killing Timer event server: {0}".format(e))

    def start_countdown_thread(self):
        if self.thread_timer_coundown is None:
            self.thread_timer_coundown = CountdownThread(self)
            self.thread_timer_coundown.signal_show_question.connect(
                self.show_widget_timer
            )
            self.thread_timer_coundown.signal_send_time.connect(
                self.change_count_widget
            )
            self.thread_timer_coundown.signal_stop_timer.connect(
                self.timer_stop
            )
            self.thread_timer_coundown.start()

    def stop_countdown_thread(self):
        if self.thread_timer_coundown is not None:
            self.thread_timer_coundown.runs = False
            self.thread_timer_coundown.terminate()
            self.thread_timer_coundown.wait()
            self.thread_timer_coundown = None

    def show_widget_timer(self):
        self.widget_timer.show()
        self.widget_timer.setWindowState(QtCore.Qt.WindowMinimized)
        self.widget_timer.setWindowState(QtCore.Qt.WindowActive)
        # self.widget_timer.activateWindow()

    def change_count_widget(self, time):
        str_time = str(time).replace(".0", "")
        self.widget_timer.lbl_rest_time.setText(str_time)

    def timer_started(self):
        self.start_countdown_thread()

    def timer_stopped(self):
        self.stop_countdown_thread()

    def timer_stop(self):
        if self.thread_timer is not None:
            self.widget_timer.main_context = False
            self.widget_timer.refresh_context()
            self.thread_timer.signal_stop_timer.emit()
        if self.thread_timer_coundown is not None:
            self.stop_countdown_thread()

    def timer_restart(self):
        if self.thread_timer is not None:
            self.thread_timer.signal_restart_timer.emit()

        self.timer_started()

    def timer_continue(self):
        if self.thread_timer_coundown is not None:
            self.thread_timer_coundown.signal_continue_timer.emit()


class FtrackEventsThread(QtCore.QThread):
    # Senders
    signal_timer_started = QtCore.Signal()
    signal_timer_stopped = QtCore.Signal()
    # Listeners
    signal_stop_timer = QtCore.Signal()
    signal_restart_timer = QtCore.Signal()

    def __init__(self, parent):
        super(FtrackEventsThread, self).__init__()
        cred = credentials._get_credentials()
        self.username = cred['username']
        self.signal_stop_timer.connect(self.ftrack_stop_timer)
        self.signal_restart_timer.connect(self.ftrack_restart_timer)
        self.user = None
        self.last_task = None

    def run(self):
        self.timer_session = ftrack_api.Session(auto_connect_event_hub=True)
        self.timer_session.event_hub.subscribe(
            'topic=ftrack.update and source.user.username={}'.format(
                self.username
            ),
            self.event_handler)

        user_query = 'User where username is "{}"'.format(self.username)
        self.user = self.timer_session.query(user_query).one()

        timer_query = 'Timer where user.username is "{}"'.format(self.username)
        timer = self.timer_session.query(timer_query).first()
        if timer is not None:
            self.last_task = timer['context']
            self.signal_timer_started.emit()

        self.timer_session.event_hub.wait()

    def event_handler(self, event):
        try:
            if event['data']['entities'][0]['objectTypeId'] != 'timer':
                return
        except Exception:
            return

        new = event['data']['entities'][0]['changes']['start']['new']
        old = event['data']['entities'][0]['changes']['start']['old']

        if old is None and new is None:
            return

        timer_query = 'Timer where user.username is "{}"'.format(self.username)
        timer = self.timer_session.query(timer_query).first()
        if timer is not None:
            self.last_task = timer['context']

        if old is None:
            self.signal_timer_started.emit()
        elif new is None:
            self.signal_timer_stopped.emit()

    def ftrack_stop_timer(self):
        try:
            self.user.stop_timer()
            self.timer_session.commit()
        except Exception as e:
            log.debug("Timer stop had issues: {}".format(e))

    def ftrack_restart_timer(self):
        try:
            if (self.last_task is not None) and (self.user is not None):
                self.user.start_timer(self.last_task)
                self.timer_session.commit()
        except Exception as e:
            log.debug("Timer stop had issues: {}".format(e))


class CountdownThread(QtCore.QThread):
    # Senders
    signal_show_question = QtCore.Signal()
    signal_send_time = QtCore.Signal(object)
    signal_stop_timer = QtCore.Signal()
    signal_stop_countdown = QtCore.Signal()
    # Listeners
    signal_reset_timer = QtCore.Signal()
    signal_continue_timer = QtCore.Signal()

    def __init__(self, parent):
        super(CountdownThread, self).__init__()

        self.runs = True
        self.over_line = False
        config_data = self.load_timer_values()
        self.count_length = config_data['full_time']*60
        self.border_line = config_data['message_time']*60 + 1
        self.reset_count()
        self.signal_reset_timer.connect(self.reset_count)
        self.signal_continue_timer.connect(self.continue_timer)

    def continue_timer(self):
        self.over_line = False
        self.reset_count()

    def reset_count(self):
        if self.over_line is True:
            self.actual = self.border_line
        else:
            self.actual = self.count_length

    def stop(self):
        self.runs = False

    def run(self):
        thread_mouse = MouseThread(self)
        thread_mouse.start()
        thread_keyboard = KeyboardThread(self)
        thread_keyboard.start()
        while self.runs:
            if self.actual == self.border_line:
                self.signal_show_question.emit()
                self.over_line = True

            if self.actual <= self.border_line:
                self.signal_send_time.emit(self.actual)

            time.sleep(1)
            self.actual -= 1

            if self.actual == 0:
                self.runs = False
                self.signal_stop_timer.emit()

        thread_mouse.signal_stop.emit()
        thread_mouse.terminate()
        thread_mouse.wait()
        thread_keyboard.signal_stop.emit()
        thread_keyboard.terminate()
        thread_keyboard.wait()

    def load_timer_values(self):
        templates = os.environ['PYPE_STUDIO_TEMPLATES']
        path_items = [templates, 'presets', 'ftrack', 'ftrack_config.json']
        filepath = os.path.sep.join(path_items)
        data = dict()
        try:
            with open(filepath) as data_file:
                json_dict = json.load(data_file)
                data = json_dict['timer']
        except Exception as e:
            msg = (
                'Loading "Ftrack Config file" Failed.'
                ' Please check log for more information.'
                ' Times are set to default.'
            )
            log.warning("{} - {}".format(msg, str(e)))

        data = self.validate_timer_values(data)

        return data

    def validate_timer_values(self, data):
        # default values
        if 'full_time' not in data:
            data['full_time'] = 15
        if 'message_time' not in data:
            data['message_time'] = 0.5

        # minimum values
        if data['full_time'] < 2:
            data['full_time'] = 2
        # message time is earlier that full time
        if data['message_time'] > data['full_time']:
            data['message_time'] = data['full_time'] - 0.5
        return data


class MouseThread(QtCore.QThread):
    signal_stop = QtCore.Signal()

    def __init__(self, parent):
        super(MouseThread, self).__init__()
        self.parent = parent
        self.signal_stop.connect(self.stop)
        self.m_listener = None

    def stop(self):
        if self.m_listener is not None:
            self.m_listener.stop()

    def on_move(self, posx, posy):
        self.parent.signal_reset_timer.emit()

    def run(self):
        self.m_listener = mouse.Listener(on_move=self.on_move)
        self.m_listener.start()


class KeyboardThread(QtCore.QThread):
    signal_stop = QtCore.Signal()

    def __init__(self, parent):
        super(KeyboardThread, self).__init__()
        self.parent = parent
        self.signal_stop.connect(self.stop)
        self.k_listener = None

    def stop(self):
        if self.k_listener is not None:
            self.k_listener.stop()

    def on_press(self, key):
        self.parent.signal_reset_timer.emit()

    def run(self):
        self.k_listener = keyboard.Listener(on_press=self.on_press)
        self.k_listener.start()


class StopTimer(QtWidgets.QWidget):

    SIZE_W = 300
    SIZE_H = 160

    def __init__(self, parent=None):

        super(StopTimer, self).__init__()

        self.main_context = True
        self.parent = parent
        self.setWindowIcon(self.parent.parent.icon)
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
        self.refresh_context()
        self.setWindowTitle('Pype - Stop Ftrack timer')

    def _main(self):
        self.main = QtWidgets.QVBoxLayout()
        self.main.setObjectName('main')

        self.form = QtWidgets.QFormLayout()
        self.form.setContentsMargins(10, 15, 10, 5)
        self.form.setObjectName('form')

        msg_info = 'You didn\'t work for a long time.'
        msg_question = 'Would you like to stop Ftrack timer?'
        msg_stopped = (
            'Your Ftrack timer was stopped. Do you want to start again?'
        )

        self.lbl_info = QtWidgets.QLabel(msg_info)
        self.lbl_info.setFont(self.font)
        self.lbl_info.setTextFormat(QtCore.Qt.RichText)
        self.lbl_info.setObjectName("lbl_info")
        self.lbl_info.setWordWrap(True)

        self.lbl_question = QtWidgets.QLabel(msg_question)
        self.lbl_question.setFont(self.font)
        self.lbl_question.setTextFormat(QtCore.Qt.RichText)
        self.lbl_question.setObjectName("lbl_question")
        self.lbl_question.setWordWrap(True)

        self.lbl_stopped = QtWidgets.QLabel(msg_stopped)
        self.lbl_stopped.setFont(self.font)
        self.lbl_stopped.setTextFormat(QtCore.Qt.RichText)
        self.lbl_stopped.setObjectName("lbl_stopped")
        self.lbl_stopped.setWordWrap(True)

        self.lbl_rest_time = QtWidgets.QLabel("")
        self.lbl_rest_time.setFont(self.font)
        self.lbl_rest_time.setTextFormat(QtCore.Qt.RichText)
        self.lbl_rest_time.setObjectName("lbl_rest_time")
        self.lbl_rest_time.setWordWrap(True)
        self.lbl_rest_time.setAlignment(QtCore.Qt.AlignCenter)

        self.form.addRow(self.lbl_info)
        self.form.addRow(self.lbl_question)
        self.form.addRow(self.lbl_stopped)
        self.form.addRow(self.lbl_rest_time)

        self.group_btn = QtWidgets.QHBoxLayout()
        self.group_btn.addStretch(1)
        self.group_btn.setObjectName("group_btn")

        self.btn_stop = QtWidgets.QPushButton("Stop timer")
        self.btn_stop.setToolTip('Stop\'s Ftrack timer')
        self.btn_stop.clicked.connect(self.stop_timer)

        self.btn_continue = QtWidgets.QPushButton("Continue")
        self.btn_continue.setToolTip('Timer will continue')
        self.btn_continue.clicked.connect(self.continue_timer)

        self.btn_close = QtWidgets.QPushButton("Close")
        self.btn_close.setToolTip('Close window')
        self.btn_close.clicked.connect(self.close_widget)

        self.btn_restart = QtWidgets.QPushButton("Start timer")
        self.btn_restart.setToolTip('Timer will be started again')
        self.btn_restart.clicked.connect(self.restart_timer)

        self.group_btn.addWidget(self.btn_continue)
        self.group_btn.addWidget(self.btn_stop)
        self.group_btn.addWidget(self.btn_restart)
        self.group_btn.addWidget(self.btn_close)

        self.main.addLayout(self.form)
        self.main.addLayout(self.group_btn)

        return self.main

    def refresh_context(self):
        self.lbl_question.setVisible(self.main_context)
        self.lbl_rest_time.setVisible(self.main_context)
        self.lbl_stopped.setVisible(not self.main_context)

        self.btn_continue.setVisible(self.main_context)
        self.btn_stop.setVisible(self.main_context)
        self.btn_restart.setVisible(not self.main_context)
        self.btn_close.setVisible(not self.main_context)

    def stop_timer(self):
        self.parent.timer_stop()
        self.close_widget()

    def restart_timer(self):
        self.parent.timer_restart()
        self.close_widget()

    def continue_timer(self):
        self.parent.timer_continue()
        self.close_widget()

    def closeEvent(self, event):
        event.ignore()
        if self.main_context is True:
            self.continue_timer()
        else:
            self.close_widget()

    def close_widget(self):
        self.main_context = True
        self.refresh_context()
        self.hide()
