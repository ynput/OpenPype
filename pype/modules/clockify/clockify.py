import os
import threading
from pype.api import Logger
from avalon import style
from Qt import QtWidgets
from . import ClockifySettings, ClockifyAPI, MessageWidget


class ClockifyModule:

    def __init__(self, main_parent=None, parent=None):
        self.log = Logger().get_logger(self.__class__.__name__, "PypeTray")

        self.main_parent = main_parent
        self.parent = parent
        self.clockapi = ClockifyAPI()
        self.message_widget = None
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
        self.bool_timer_run = False
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
                elif self.bool_timer_run is False:
                    actual_timer = self.clockapi.get_in_progress()
                    if not actual_timer:
                        continue

                    actual_proj_id = actual_timer["projectId"]
                    if not actual_proj_id:
                        continue

                    project = self.clockapi.get_project_by_id(actual_proj_id)
                    if project and project.get("code") == 501:
                        continue

                    project_name = project["name"]

                    actual_timer_hierarchy = actual_timer["description"]
                    hierarchy_items = actual_timer_hierarchy.split("/")
                    # Each pype timer must have at least 2 items!
                    if len(hierarchy_items) < 2:
                        continue
                    task_name = hierarchy_items[-1]
                    hierarchy = hierarchy_items[:-1]

                    task_type = None
                    if len(actual_timer.get("tags", [])) > 0:
                        task_type = actual_timer["tags"][0].get("name")
                    data = {
                        "task_name": task_name,
                        "hierarchy": hierarchy,
                        "project_name": project_name,
                        "task_type": task_type
                    }

                    self.timer_started(data)

                self.bool_timer_run = bool_timer_run
                self.set_menu_visibility()
            time.sleep(5)

    def stop_timer(self):
        self.clockapi.finish_time_entry()
        if self.bool_timer_run:
            self.timer_stopped()

    def signed_in(self):
        if hasattr(self, 'timer_manager'):
            if not self.timer_manager:
                return

            if not self.timer_manager.last_task:
                return

            if self.timer_manager.is_running:
                self.start_timer_manager(self.timer_manager.last_task)

    def start_timer(self, input_data):
        # If not api key is not entered then skip
        if not self.clockapi.get_api_key():
            return

        actual_timer = self.clockapi.get_in_progress()
        actual_timer_hierarchy = None
        actual_project_id = None
        if actual_timer is not None:
            actual_timer_hierarchy = actual_timer.get("description")
            actual_project_id = actual_timer.get("projectId")

        # Concatenate hierarchy and task to get description
        desc_items = [val for val in input_data.get("hierarchy", [])]
        desc_items.append(input_data["task_name"])
        description = "/".join(desc_items)

        # Check project existence
        project_name = input_data["project_name"]
        project_id = self.clockapi.get_project_id(project_name)
        if not project_id:
            self.log.warning((
                "Project \"{}\" was not found in Clockify. Timer won't start."
            ).format(project_name))

            msg = (
                "Project <b>\"{}\"</b> is not in Clockify Workspace <b>\"{}\"</b>."
                "<br><br>Please inform your Project Manager."
            ).format(project_name, str(self.clockapi.workspace))

            self.message_widget = MessageWidget(
                self.main_parent, msg, "Clockify - Info Message"
            )
            self.message_widget.closed.connect(self.on_message_widget_close)
            self.message_widget.show()

            return

        if (
            actual_timer is not None and
            description == actual_timer_hierarchy and
            project_id == actual_project_id
        ):
            return

        tag_ids = []
        task_tag_id = self.clockapi.get_tag_id(input_data["task_type"])
        if task_tag_id is not None:
            tag_ids.append(task_tag_id)

        self.clockapi.start_time_entry(
            description, project_id, tag_ids=tag_ids
        )

    def on_message_widget_close(self):
        self.message_widget = None

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
