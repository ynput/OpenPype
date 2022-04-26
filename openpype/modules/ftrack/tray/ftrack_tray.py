import os
import time
import datetime
import threading
from Qt import QtCore, QtWidgets, QtGui

import ftrack_api
from ..ftrack_server.lib import check_ftrack_url
from ..ftrack_server import socket_thread
from ..lib import credentials
from ..ftrack_module import FTRACK_MODULE_DIR
from . import login_dialog

from openpype.api import Logger, resources


log = Logger().get_logger("FtrackModule")


class FtrackTrayWrapper:
    def __init__(self, module):
        self.module = module

        self.thread_action_server = None
        self.thread_socket_server = None
        self.thread_timer = None

        self.bool_logged = False
        self.bool_action_server_running = False
        self.bool_action_thread_running = False
        self.bool_timer_event = False

        self.widget_login = login_dialog.CredentialsDialog(module)
        self.widget_login.login_changed.connect(self.on_login_change)
        self.widget_login.logout_signal.connect(self.on_logout)

        self.action_credentials = None
        self.tray_server_menu = None
        self.icon_logged = QtGui.QIcon(
            resources.get_resource("icons", "circle_green.png")
        )
        self.icon_not_logged = QtGui.QIcon(
            resources.get_resource("icons", "circle_orange.png")
        )

    def show_login_widget(self):
        self.widget_login.show()
        self.widget_login.activateWindow()
        self.widget_login.raise_()

    def validate(self):
        validation = False
        cred = credentials.get_credentials()
        ft_user = cred.get("username")
        ft_api_key = cred.get("api_key")
        validation = credentials.check_credentials(ft_user, ft_api_key)
        if validation:
            self.widget_login.set_credentials(ft_user, ft_api_key)
            self.module.set_credentials_to_env(ft_user, ft_api_key)
            log.info("Connected to Ftrack successfully")
            self.on_login_change()

            return validation

        if not validation and ft_user and ft_api_key:
            log.warning(
                "Current Ftrack credentials are not valid. {}: {} - {}".format(
                    str(os.environ.get("FTRACK_SERVER")), ft_user, ft_api_key
                )
            )

        log.info("Please sign in to Ftrack")
        self.bool_logged = False
        self.show_login_widget()
        self.set_menu_visibility()

        return validation

    # Necessary - login_dialog works with this method after logging in
    def on_login_change(self):
        self.bool_logged = True

        if self.action_credentials:
            self.action_credentials.setIcon(self.icon_logged)
            self.action_credentials.setToolTip(
                "Logged as user \"{}\"".format(
                    self.widget_login.user_input.text()
                )
            )

        self.set_menu_visibility()
        self.start_action_server()

    def on_logout(self):
        credentials.clear_credentials()
        self.stop_action_server()

        if self.action_credentials:
            self.action_credentials.setIcon(self.icon_not_logged)
            self.action_credentials.setToolTip("Logged out")

        log.info("Logged out of Ftrack")
        self.bool_logged = False
        self.set_menu_visibility()

    # Actions part
    def start_action_server(self):
        if self.thread_action_server is None:
            self.thread_action_server = threading.Thread(
                target=self.set_action_server
            )
            self.thread_action_server.start()

    def set_action_server(self):
        if self.bool_action_server_running:
            return

        self.bool_action_server_running = True
        self.bool_action_thread_running = False

        ftrack_url = self.module.ftrack_url
        os.environ["FTRACK_SERVER"] = ftrack_url

        parent_file_path = os.path.dirname(
            os.path.dirname(os.path.realpath(__file__))
        )

        min_fail_seconds = 5
        max_fail_count = 3
        wait_time_after_max_fail = 10

        # Threads data
        thread_name = "ActionServerThread"
        thread_port = 10021
        subprocess_path = (
            "{}/scripts/sub_user_server.py".format(FTRACK_MODULE_DIR)
        )
        if self.thread_socket_server is not None:
            self.thread_socket_server.stop()
            self.thread_socket_server.join()
            self.thread_socket_server = None

        last_failed = datetime.datetime.now()
        failed_count = 0

        ftrack_accessible = False
        printed_ftrack_error = False

        # Main loop
        while True:
            if not self.bool_action_server_running:
                log.debug("Action server was pushed to stop.")
                break

            # Check if accessible Ftrack and Mongo url
            if not ftrack_accessible:
                ftrack_accessible = check_ftrack_url(ftrack_url)

            # Run threads only if Ftrack is accessible
            if not ftrack_accessible:
                if not printed_ftrack_error:
                    log.warning("Can't access Ftrack {}".format(ftrack_url))

                if self.thread_socket_server is not None:
                    self.thread_socket_server.stop()
                    self.thread_socket_server.join()
                    self.thread_socket_server = None
                    self.bool_action_thread_running = False
                    self.set_menu_visibility()

                printed_ftrack_error = True

                time.sleep(1)
                continue

            printed_ftrack_error = False

            # Run backup thread which does not requeire mongo to work
            if self.thread_socket_server is None:
                if failed_count < max_fail_count:
                    self.thread_socket_server = socket_thread.SocketThread(
                        thread_name, thread_port, subprocess_path
                    )
                    self.thread_socket_server.start()
                    self.bool_action_thread_running = True
                    self.set_menu_visibility()

                elif failed_count == max_fail_count:
                    log.warning((
                        "Action server failed {} times."
                        " I'll try to run again {}s later"
                    ).format(
                        str(max_fail_count), str(wait_time_after_max_fail))
                    )
                    failed_count += 1

                elif ((
                    datetime.datetime.now() - last_failed
                ).seconds > wait_time_after_max_fail):
                    failed_count = 0

            # If thread failed test Ftrack and Mongo connection
            elif not self.thread_socket_server.isAlive():
                self.thread_socket_server.join()
                self.thread_socket_server = None
                ftrack_accessible = False

                self.bool_action_thread_running = False
                self.set_menu_visibility()

                _last_failed = datetime.datetime.now()
                delta_time = (_last_failed - last_failed).seconds
                if delta_time < min_fail_seconds:
                    failed_count += 1
                else:
                    failed_count = 0
                last_failed = _last_failed

            time.sleep(1)

        self.bool_action_thread_running = False
        self.bool_action_server_running = False
        self.set_menu_visibility()

    def reset_action_server(self):
        self.stop_action_server()
        self.start_action_server()

    def stop_action_server(self):
        try:
            self.bool_action_server_running = False
            if self.thread_socket_server is not None:
                self.thread_socket_server.stop()
                self.thread_socket_server.join()
                self.thread_socket_server = None

            if self.thread_action_server is not None:
                self.thread_action_server.join()
                self.thread_action_server = None

            log.info("Ftrack action server was forced to stop")

        except Exception:
            log.warning(
                "Error has happened during Killing action server",
                exc_info=True
            )

    # Definition of Tray menu
    def tray_menu(self, parent_menu):
        # Menu for Tray App
        tray_menu = QtWidgets.QMenu("Ftrack", parent_menu)

        # Actions - basic
        action_credentials = QtWidgets.QAction("Credentials", tray_menu)
        action_credentials.triggered.connect(self.show_login_widget)
        if self.bool_logged:
            icon = self.icon_logged
        else:
            icon = self.icon_not_logged
        action_credentials.setIcon(icon)
        tray_menu.addAction(action_credentials)
        self.action_credentials = action_credentials

        # Actions - server
        tray_server_menu = tray_menu.addMenu("Action server")

        self.action_server_run = QtWidgets.QAction(
            "Run action server", tray_server_menu
        )
        self.action_server_reset = QtWidgets.QAction(
            "Reset action server", tray_server_menu
        )
        self.action_server_stop = QtWidgets.QAction(
            "Stop action server", tray_server_menu
        )

        self.action_server_run.triggered.connect(self.start_action_server)
        self.action_server_reset.triggered.connect(self.reset_action_server)
        self.action_server_stop.triggered.connect(self.stop_action_server)

        tray_server_menu.addAction(self.action_server_run)
        tray_server_menu.addAction(self.action_server_reset)
        tray_server_menu.addAction(self.action_server_stop)

        self.tray_server_menu = tray_server_menu
        self.bool_logged = False
        self.set_menu_visibility()

        parent_menu.addMenu(tray_menu)

    def tray_exit(self):
        self.stop_action_server()
        self.stop_timer_thread()

    # Definition of visibility of each menu actions
    def set_menu_visibility(self):
        self.tray_server_menu.menuAction().setVisible(self.bool_logged)
        if self.bool_logged is False:
            if self.bool_timer_event is True:
                self.stop_timer_thread()
            return

        self.action_server_run.setVisible(not self.bool_action_server_running)
        self.action_server_reset.setVisible(self.bool_action_thread_running)
        self.action_server_stop.setVisible(self.bool_action_server_running)

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

    def changed_user(self):
        self.stop_action_server()
        self.module.set_credentials_to_env(None, None)
        self.validate()

    def start_timer_manager(self, data):
        if self.thread_timer is not None:
            self.thread_timer.ftrack_start_timer(data)

    def stop_timer_manager(self):
        if self.thread_timer is not None:
            self.thread_timer.ftrack_stop_timer()

    def timer_started(self, data):
        self.module.timer_started(data)

    def timer_stopped(self):
        self.module.timer_stopped()


class FtrackEventsThread(QtCore.QThread):
    # Senders
    signal_timer_started = QtCore.Signal(object)
    signal_timer_stopped = QtCore.Signal()

    def __init__(self, parent):
        super(FtrackEventsThread, self).__init__()
        cred = credentials.get_credentials()
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
