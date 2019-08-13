import os
import threading
from pypeapp import style
from Qt import QtWidgets
from pype.clockify import ClockifySettings, ClockifyAPI


class ClockifyModule:

    def __init__(self, main_parent=None, parent=None):
        self.main_parent = main_parent
        self.parent = parent
        self.clockapi = ClockifyAPI()
        self.widget_settings = ClockifySettings(main_parent, self)
        self.widget_settings_required = None

        self.thread_timer_check = None
        # Bools
        self.bool_thread_check_running = False
        self.bool_api_key_set = False
        self.bool_workspace_set = False
        self.bool_timer_run = False

        self.clockapi.set_master(self)
        self.bool_api_key_set = self.clockapi.set_api()

    def tray_start(self):
        if self.bool_api_key_set is False:
            self.show_settings()
            return

        self.bool_workspace_set = self.clockapi.workspace_id is not None
        if self.bool_workspace_set is False:
            return

        self.start_timer_check()

        self.set_menu_visibility()

    def process_modules(self, modules):
        if 'FtrackModule' in modules:
            actions_path = os.path.sep.join([
                os.path.dirname(__file__),
                'ftrack_actions'
            ])
            current = os.environ.get('FTRACK_ACTIONS_PATH', '')
            if current:
                current += os.pathsep
            os.environ['FTRACK_ACTIONS_PATH'] = current + actions_path

        if 'AvalonApps' in modules:
            from launcher import lib
            actions_path = os.path.sep.join([
                os.path.dirname(__file__),
                'launcher_actions'
            ])
            current = os.environ.get('AVALON_ACTIONS', '')
            if current:
                current += os.pathsep
            os.environ['AVALON_ACTIONS'] = current + actions_path

        if 'TimersManager' in modules:
            self.timer_manager = modules['TimersManager']
            self.timer_manager.add_module(self)

    def timer_started(self, data):
        if hasattr(self, 'timer_manager'):
            self.timer_manager.start_timers(data)

    def timer_stopped(self):
        if hasattr(self, 'timer_manager'):
            self.timer_manager.stop_timers()

    def start_timer_check(self):
        self.bool_thread_check_running = True
        if self.thread_timer_check is None:
            self.thread_timer_check = threading.Thread(
                target=self.check_running
            )
            self.thread_timer_check.daemon = True
            self.thread_timer_check.start()

    def stop_timer_check(self):
        self.bool_thread_check_running = True
        if self.thread_timer_check is not None:
            self.thread_timer_check.join()
            self.thread_timer_check = None

    def check_running(self):
        import time
        while self.bool_thread_check_running is True:
            if self.clockapi.get_in_progress() is not None:
                self.bool_timer_run = True
            else:
                self.bool_timer_run = False
            self.set_menu_visibility()
            time.sleep(5)

    def stop_timer(self):
        self.clockapi.finish_time_entry()
        self.bool_timer_run = False

    # Definition of Tray menu
    def tray_menu(self, parent_menu):
        # Menu for Tray App
        self.menu = QtWidgets.QMenu('Clockify', parent_menu)
        self.menu.setProperty('submenu', 'on')
        self.menu.setStyleSheet(style.load_stylesheet())

        # Actions
        self.aShowSettings = QtWidgets.QAction(
            "Settings", self.menu
        )
        self.aStopTimer = QtWidgets.QAction(
            "Stop timer", self.menu
        )

        self.menu.addAction(self.aShowSettings)
        self.menu.addAction(self.aStopTimer)

        self.aShowSettings.triggered.connect(self.show_settings)
        self.aStopTimer.triggered.connect(self.stop_timer)

        self.set_menu_visibility()

        parent_menu.addMenu(self.menu)

    def show_settings(self):
        self.widget_settings.input_api_key.setText(self.clockapi.get_api_key())
        self.widget_settings.show()

    def set_menu_visibility(self):
        self.aStopTimer.setVisible(self.bool_timer_run)
