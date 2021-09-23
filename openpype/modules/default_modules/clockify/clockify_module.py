import os
import threading
import time

from .clockify_api import ClockifyAPI
from .constants import (
    CLOCKIFY_FTRACK_USER_PATH,
    CLOCKIFY_FTRACK_SERVER_PATH
)
from openpype.modules import OpenPypeModule
from openpype_interfaces import (
    ITrayModule,
    IPluginPaths
)


class ClockifyModule(
    OpenPypeModule,
    ITrayModule,
    IPluginPaths
):
    name = "clockify"

    def initialize(self, modules_settings):
        clockify_settings = modules_settings[self.name]
        self.enabled = clockify_settings["enabled"]
        self.workspace_name = clockify_settings["workspace_name"]

        if self.enabled and not self.workspace_name:
            raise Exception("Clockify Workspace is not set in settings.")

        self.timer_manager = None
        self.MessageWidgetClass = None
        self.message_widget = None

        self.clockapi = ClockifyAPI(master_parent=self)

        # TimersManager attributes
        # - set `timers_manager_connector` only in `tray_init`
        self.timers_manager_connector = None
        self._timers_manager_module = None

    def get_global_environments(self):
        return {
            "CLOCKIFY_WORKSPACE": self.workspace_name
        }

    def tray_init(self):
        from .widgets import ClockifySettings, MessageWidget

        self.MessageWidgetClass = MessageWidget

        self.message_widget = None
        self.widget_settings = ClockifySettings(self.clockapi)
        self.widget_settings_required = None

        self.thread_timer_check = None
        # Bools
        self.bool_thread_check_running = False
        self.bool_api_key_set = False
        self.bool_workspace_set = False
        self.bool_timer_run = False
        self.bool_api_key_set = self.clockapi.set_api()

        # Define itself as TimersManager connector
        self.timers_manager_connector = self

    def tray_start(self):
        if self.bool_api_key_set is False:
            self.show_settings()
            return

        self.bool_workspace_set = self.clockapi.workspace_id is not None
        if self.bool_workspace_set is False:
            return

        self.start_timer_check()

        self.set_menu_visibility()

    def tray_exit(self, *_a, **_kw):
        return

    def get_plugin_paths(self):
        """Implementaton of IPluginPaths to get plugin paths."""
        actions_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "launcher_actions"
        )
        return {
            "actions": [actions_path]
        }

    def get_ftrack_event_handler_paths(self):
        """Function for Ftrack module to add ftrack event handler paths."""
        return {
            "user": [CLOCKIFY_FTRACK_USER_PATH],
            "server": [CLOCKIFY_FTRACK_SERVER_PATH]
        }

    def clockify_timer_stopped(self):
        self.bool_timer_run = False
        # Call `ITimersManager` method
        self.timer_stopped()

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
        while self.bool_thread_check_running is True:
            bool_timer_run = False
            if self.clockapi.get_in_progress() is not None:
                bool_timer_run = True

            if self.bool_timer_run != bool_timer_run:
                if self.bool_timer_run is True:
                    self.clockify_timer_stopped()
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
                    # Call `ITimersManager` method
                    self.timer_started(data)

                self.bool_timer_run = bool_timer_run
                self.set_menu_visibility()
            time.sleep(5)

    def signed_in(self):
        if not self.timer_manager:
            return

        if not self.timer_manager.last_task:
            return

        if self.timer_manager.is_running:
            self.start_timer_manager(self.timer_manager.last_task)

    def on_message_widget_close(self):
        self.message_widget = None

    # Definition of Tray menu
    def tray_menu(self, parent_menu):
        # Menu for Tray App
        from Qt import QtWidgets
        menu = QtWidgets.QMenu("Clockify", parent_menu)
        menu.setProperty("submenu", "on")

        # Actions
        action_show_settings = QtWidgets.QAction("Settings", menu)
        action_stop_timer = QtWidgets.QAction("Stop timer", menu)

        menu.addAction(action_show_settings)
        menu.addAction(action_stop_timer)

        action_show_settings.triggered.connect(self.show_settings)
        action_stop_timer.triggered.connect(self.stop_timer)

        self.action_stop_timer = action_stop_timer

        self.set_menu_visibility()

        parent_menu.addMenu(menu)

    def show_settings(self):
        self.widget_settings.input_api_key.setText(self.clockapi.get_api_key())
        self.widget_settings.show()

    def set_menu_visibility(self):
        self.action_stop_timer.setVisible(self.bool_timer_run)

    # --- TimersManager connection methods ---
    def register_timers_manager(self, timer_manager_module):
        """Store TimersManager for future use."""
        self._timers_manager_module = timer_manager_module

    def timer_started(self, data):
        """Tell TimersManager that timer started."""
        if self._timers_manager_module is not None:
            self._timers_manager_module.timer_started(self._module.id, data)

    def timer_stopped(self):
        """Tell TimersManager that timer stopped."""
        if self._timers_manager_module is not None:
            self._timers_manager_module.timer_stopped(self._module.id)

    def stop_timer(self):
        """Called from TimersManager to stop timer."""
        self.clockapi.finish_time_entry()

    def start_timer(self, input_data):
        """Called from TimersManager to start timer."""
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

            if not self.MessageWidgetClass:
                return

            msg = (
                "Project <b>\"{}\"</b> is not"
                " in Clockify Workspace <b>\"{}\"</b>."
                "<br><br>Please inform your Project Manager."
            ).format(project_name, str(self.clockapi.workspace_name))

            self.message_widget = self.MessageWidgetClass(
                msg, "Clockify - Info Message"
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
