import os
import threading
from app import style
from app.vendor.Qt import QtWidgets
from pype.clockify import ClockifySettings, ClockifyAPI


class ClockifyModule:

    def __init__(self, main_parent=None, parent=None):
        self.main_parent = main_parent
        self.parent = parent
        self.clockapi = ClockifyAPI()
        self.widget_settings = ClockifySettings(main_parent, self)

        self.thread_timer_check = None
        # Bools
        self.bool_thread_check_running = False
        self.bool_api_key_set = False
        self.bool_workspace_set = False
        self.bool_timer_run = False

    def start_up(self):
        self.bool_api_key_set = self.clockapi.set_api()
        if self.bool_api_key_set is False:
            self.show_settings()
            return

        workspace = os.environ.get('CLOCKIFY_WORKSPACE', None)
        self.bool_workspace_set = self.clockapi.set_workspace(workspace)
        if self.bool_workspace_set is False:
            # TODO show message to user
            print("Nope Workspace: clockify.py - line 29")
            return

        self.bool_thread_check_running = True
        self.start_timer_check()

        self.set_menu_visibility()

    def change_timer_run(self, bool_run):
        self.bool_timer_run = bool_run
        self.set_menu_visibility()

    def start_timer_check(self):
        if self.thread_timer_check is None:
            self.thread_timer_check = threading.Thread(
                target=self.check_running
            )
            self.thread_timer_check.daemon = True
            self.thread_timer_check.start()

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

    # Definition of Tray menu
    def tray_menu(self, parent):
        # Menu for Tray App
        self.menu = QtWidgets.QMenu('Clockify', parent)
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

        return self.menu

    def show_settings(self):
        self.widget_settings.input_api_key.setText(self.clockapi.get_api_key())
        self.widget_settings.show()

    def set_menu_visibility(self):
        self.aStopTimer.setVisible(self.bool_timer_run)
