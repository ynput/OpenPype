import os
import json
import threading
import time
from Qt import QtCore, QtGui, QtWidgets

from pype.vendor import ftrack_api
from pypeapp import style
from pype.ftrack import FtrackServer, credentials
from . import login_dialog

from pype import api as pype


log = pype.Logger().get_logger("FtrackModule", "ftrack")


class FtrackModule:
    def __init__(self, main_parent=None, parent=None):
        self.parent = parent
        self.widget_login = login_dialog.Login_Dialog_ui(self)
        self.action_server = FtrackServer('action')
        self.thread_action_server = None
        self.thread_timer = None

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
        except Exception as exc:
            log.error(
                "Ftrack Action server crashed! Please try to start again.",
                exc_info=True
            )
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
    def tray_menu(self, parent_menu):
        # Menu for Tray App
        self.menu = QtWidgets.QMenu('Ftrack', parent_menu)
        self.menu.setProperty('submenu', 'on')

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

        parent_menu.addMenu(self.menu)

    def tray_start(self):
        self.validate()

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

    def process_modules(self, modules):
        if 'TimersManager' in modules:
            self.timer_manager = modules['TimersManager']
            self.timer_manager.add_module(self)

    def start_timer_manager(self, data):
        if self.thread_timer is not None:
            self.thread_timer.ftrack_start_timer(data)

    def stop_timer_manager(self):
        if self.thread_timer is not None:
            self.thread_timer.ftrack_stop_timer()

    def timer_started(self, data):
        if hasattr(self, 'timer_manager'):
            self.timer_manager.start_timers(data)

    def timer_stopped(self):
        if hasattr(self, 'timer_manager'):
            self.timer_manager.stop_timers()


class FtrackEventsThread(QtCore.QThread):
    # Senders
    signal_timer_started = QtCore.Signal(object)
    signal_timer_stopped = QtCore.Signal()

    def __init__(self, parent):
        super(FtrackEventsThread, self).__init__()
        cred = credentials._get_credentials()
        self.username = cred['username']
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
            self.signal_timer_started.emit(
                self.get_data_from_task(self.last_task)
            )

        self.timer_session.event_hub.wait()

    def get_data_from_task(self, task_entity):
        data = {}
        data['task_name'] = task_entity['name']
        data['task_type'] = task_entity['type']['name']
        data['project_name'] = task_entity['project']['full_name']
        data['hierarchy'] = self.get_parents(task_entity['parent'])

        return data

    def get_parents(self, entity):
        output = []
        if entity.entity_type.lower() == 'project':
            return output
        output.extend(self.get_parents(entity['parent']))
        output.append(entity['name'])

        return output

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
            self.signal_timer_started.emit(
                self.get_data_from_task(self.last_task)
            )
        elif new is None:
            self.signal_timer_stopped.emit()

    def ftrack_stop_timer(self):
        actual_timer = self.timer_session.query(
            'Timer where user_id = "{0}"'.format(self.user['id'])
        ).first()

        if actual_timer is not None:
            self.user.stop_timer()
            self.timer_session.commit()
            self.signal_timer_stopped.emit()

    def ftrack_start_timer(self, input_data):
        if self.user is None:
            return

        actual_timer = self.timer_session.query(
            'Timer where user_id = "{0}"'.format(self.user['id'])
        ).first()
        if (
            actual_timer is not None and
            input_data['task_name'] == self.last_task['name'] and
            input_data['hierarchy'][-1] == self.last_task['parent']['name']
        ):
            return

        input_data['entity_name'] = input_data['hierarchy'][-1]

        task_query = (
            'Task where name is "{task_name}"'
            ' and parent.name is "{entity_name}"'
            ' and project.full_name is "{project_name}"'
        ).format(**input_data)

        task = self.timer_session.query(task_query).one()
        self.last_task = task
        self.user.start_timer(task)
        self.timer_session.commit()
        self.signal_timer_started.emit(
            self.get_data_from_task(self.last_task)
        )
