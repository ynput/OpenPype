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

    def start_timer_manager(self, data):
        self.start_timer(data)

    def stop_timer_manager(self):
        self.stop_timer()

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
            bool_timer_run = False
            if self.clockapi.get_in_progress() is not None:
                bool_timer_run = True

            if self.bool_timer_run != bool_timer_run:
                if self.bool_timer_run is True:
                    self.timer_stopped()
                else:
                    actual_timer = self.clockapi.get_in_progress()
                    if not actual_timer:
                        continue

                    actual_project_id = actual_timer["projectId"]
                    project = self.clockapi.get_project_by_id(
                        actual_project_id
                    )
                    project_name = project["name"]

                    actual_timer_hierarchy = actual_timer["description"]
                    hierarchy_items = actual_timer_hierarchy.split("/")
                    task_name = hierarchy_items[-1]
                    hierarchy = hierarchy_items[:-1]

                    data = {
                        "task_name": task_name,
                        "hierarchy": hierarchy,
                        "project_name": project_name
                    }

                    self.timer_started(data)

                self.bool_timer_run = bool_timer_run
                self.set_menu_visibility()
            time.sleep(5)

    def stop_timer(self):
        self.clockapi.finish_time_entry()
        if self.bool_timer_run:
            self.timer_stopped()
        self.bool_timer_run = False

    def start_timer(self, input_data):
        actual_timer = self.clockapi.get_in_progress()
        actual_timer_hierarchy = None
        actual_project_id = None
        if actual_timer is not None:
            actual_timer_hierarchy = actual_timer.get("description")
            actual_project_id = actual_timer.get("projectId")

        desc_items = [val for val in input_data.get("hierarchy", [])]
        desc_items.append(input_data["task_name"])
        description = "/".join(desc_items)

        project_id = self.clockapi.get_project_id(input_data["project_name"])

        if (
            actual_timer is not None and
            description == actual_timer_hierarchy and
            project_id == actual_project_id
        ):
            return

        tag_ids = []
        task_tag_id = self.clockapi.get_tag_id(input_data["task_name"])
        if task_tag_id is not None:
            tag_ids.append(task_tag_id)

        self.clockapi.start_time_entry(
            description, project_id, tag_ids=tag_ids
        )

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
