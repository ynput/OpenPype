import os
from app import style
from app.vendor.Qt import QtWidgets
from pype.clockify import ClockifySettings, ClockifyAPI


class ClockifyModule:

    def __init__(self, main_parent=None, parent=None):
        self.main_parent = main_parent
        self.parent = parent
        self.clockapi = ClockifyAPI()
        self.widget_settings = ClockifySettings(main_parent, self)

        # Bools
        self.bool_api_key_set = False
        self.bool_workspace_set = False
        self.bool_timer_run = False

    def start_up(self):
        self.bool_api_key_set = self.clockapi.set_api()
        if self.bool_api_key_set is False:
            self.show_settings()
            return

        workspace = os.environ.get('CLOCKIFY_WORKSPACE', None)
        print(workspace)
        self.bool_workspace_set = self.clockapi.set_workspace(workspace)
        if self.bool_workspace_set is False:
            # TODO show message to user
            print("Nope Workspace: clockify.py - line 29")
            return
        if self.clockapi.get_in_progress() is not None:
            self.bool_timer_run = True

        self.set_menu_visibility()

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
