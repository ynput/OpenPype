from openpype.lib import Logger
from openpype.lib.events import QueuedEventSystem
from openpype.settings import get_project_settings
from openpype.tools.ayon_utils.models import ProjectsModel, HierarchyModel

from .abstract import AbstractLauncherFrontEnd, AbstractLauncherBackend
from .models import LauncherSelectionModel, ActionsModel


class BaseLauncherController(
    AbstractLauncherFrontEnd, AbstractLauncherBackend
):
    def __init__(self):
        self._project_settings = {}
        self._event_system = None
        self._log = None

        self._selection_model = LauncherSelectionModel(self)
        self._projects_model = ProjectsModel(self)
        self._hierarchy_model = HierarchyModel(self)
        self._actions_model = ActionsModel(self)

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger(self.__class__.__name__)
        return self._log

    @property
    def event_system(self):
        """Inner event system for workfiles tool controller.

        Is used for communication with UI. Event system is created on demand.

        Returns:
            QueuedEventSystem: Event system which can trigger callbacks
                for topics.
        """

        if self._event_system is None:
            self._event_system = QueuedEventSystem()
        return self._event_system

    # ---------------------------------
    # Implementation of abstract methods
    # ---------------------------------
    # Events system
    def emit_event(self, topic, data=None, source=None):
        """Use implemented event system to trigger event."""

        if data is None:
            data = {}
        self.event_system.emit(topic, data, source)

    def register_event_callback(self, topic, callback):
        self.event_system.add_callback(topic, callback)

    # Entity items for UI
    def get_project_items(self, sender=None):
        return self._projects_model.get_project_items(sender)

    def get_folder_items(self, project_name, sender=None):
        return self._hierarchy_model.get_folder_items(project_name, sender)

    def get_task_items(self, project_name, folder_id, sender=None):
        return self._hierarchy_model.get_task_items(
            project_name, folder_id, sender)

    # Project settings for applications actions
    def get_project_settings(self, project_name):
        if project_name in self._project_settings:
            return self._project_settings[project_name]
        settings = get_project_settings(project_name)
        self._project_settings[project_name] = settings
        return settings

    # Entity for backend
    def get_project_entity(self, project_name):
        return self._projects_model.get_project_entity(project_name)

    def get_folder_entity(self, project_name, folder_id):
        return self._hierarchy_model.get_folder_entity(
            project_name, folder_id)

    def get_task_entity(self, project_name, task_id):
        return self._hierarchy_model.get_task_entity(project_name, task_id)

    # Selection methods
    def get_selected_project_name(self):
        return self._selection_model.get_selected_project_name()

    def set_selected_project(self, project_name):
        self._selection_model.set_selected_project(project_name)

    def get_selected_folder_id(self):
        return self._selection_model.get_selected_folder_id()

    def set_selected_folder(self, folder_id):
        self._selection_model.set_selected_folder(folder_id)

    def get_selected_task_id(self):
        return self._selection_model.get_selected_task_id()

    def get_selected_task_name(self):
        return self._selection_model.get_selected_task_name()

    def set_selected_task(self, task_id, task_name):
        self._selection_model.set_selected_task(task_id, task_name)

    def get_selected_context(self):
        return {
            "project_name": self.get_selected_project_name(),
            "folder_id": self.get_selected_folder_id(),
            "task_id": self.get_selected_task_id(),
            "task_name": self.get_selected_task_name(),
        }

    # Actions
    def get_action_items(self, project_name, folder_id, task_id):
        return self._actions_model.get_action_items(
            project_name, folder_id, task_id)

    def set_application_force_not_open_workfile(
        self, project_name, folder_id, task_id, action_ids, enabled
    ):
        self._actions_model.set_application_force_not_open_workfile(
            project_name, folder_id, task_id, action_ids, enabled
        )

    def trigger_action(self, project_name, folder_id, task_id, identifier):
        self._actions_model.trigger_action(
            project_name, folder_id, task_id, identifier)

    # General methods
    def refresh(self):
        self._emit_event("controller.refresh.started")

        self._project_settings = {}

        self._projects_model.reset()
        self._hierarchy_model.reset()

        self._actions_model.refresh()
        self._projects_model.refresh()

        self._emit_event("controller.refresh.finished")

    def refresh_actions(self):
        self._emit_event("controller.refresh.actions.started")

        # Refresh project settings (used for actions discovery)
        self._project_settings = {}
        # Refresh projects - they define applications
        self._projects_model.reset()
        # Refresh actions
        self._actions_model.refresh()

        self._emit_event("controller.refresh.actions.finished")

    def _emit_event(self, topic, data=None):
        self.emit_event(topic, data, "controller")
