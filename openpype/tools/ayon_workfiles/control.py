from openpype.lib import Logger
from openpype.lib.events import EventSystem
from openpype.pipeline import Anatomy, registered_host

from .abstract import AbstractWorkfileController
from .models import SelectionModel, EntitiesModel, WorkfilesModel


class BaseWorkfileController(AbstractWorkfileController):
    def __init__(self, host=None):
        if host is None:
            host = registered_host()
        self._host = host

        self._anatomy = None
        self._event_system = None
        self._log = None

        self._current_project_name = None
        self._current_folder_path = None
        self._current_folder_id = None
        self._current_task_name = None

        self._selection_model = SelectionModel(self)
        self._entities_model = EntitiesModel(self)
        self._worfiles_model = WorkfilesModel(self)

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger("WorkfilesUI")
        return self._log

    @property
    def anatomy(self):
        if self._anatomy is None:
            self._anatomy = Anatomy(self.get_current_project_name())
        return self._anatomy

    @property
    def event_system(self):
        """Inner event system for workfiles tool controller.

        Is used for communication with UI. Event system is created on demand.

        Returns:
            EventSystem: Event system which can trigger callbacks for topics.
        """

        if self._event_system is None:
            self._event_system = EventSystem()
        return self._event_system

    def emit_event(self, topic, data=None, source=None):
        """Use implemented event system to trigger event."""

        if data is None:
            data = {}
        self.event_system.emit(topic, data, source)

    def register_event_callback(self, topic, callback):
        self.event_system.add_callback(topic, callback)

    def _emit_event(self, topic, data=None):
        self.emit_event(topic, data, "controller")

    # Host information
    def get_workfile_extensions(self):
        return self._host.get_workfile_extensions()

    # Current context
    def get_current_project_name(self):
        return self._current_project_name

    def get_current_folder_id(self):
        return self._current_folder_id

    def get_current_task_name(self):
        return self._current_task_name

    # Selection information
    def get_selected_folder_id(self):
        return self._selection_model.get_selected_folder_id()

    def set_selected_folder(self, folder_id):
        self._selection_model.set_selected_folder(folder_id)

    def get_selected_task_name(self):
        return self._selection_model.get_selected_task_name()

    def set_selected_task(self, folder_id, task_id, task_name):
        return self._selection_model.set_selected_task(
            folder_id, task_id, task_name)

    def get_selected_workfile_path(self):
        return self._selection_model.get_selected_workfile_path()

    def set_selected_workfile_path(self, path):
        self._selection_model.set_selected_workfile_path(path)

    def get_selected_representation_id(self):
        return self._selection_model.get_selected_representation_id()

    def set_selected_representation_id(self, representation_id):
        self._selection_model.set_selected_representation_id(
            representation_id)

    # Model functions
    def get_folder_items(self):
        return self._entities_model.get_folder_items()

    def get_task_items(self, folder_id):
        return self._entities_model.get_tasks_items(folder_id)

    def refresh(self):
        self._emit_event("controller.refresh.started")

        context = self._host.get_current_context()

        self._current_project_name = context["project_name"]
        self._current_folder_path = context["folder_path"]
        self._current_folder_id = None
        self._current_task_name = context["task_name"]

        self._entities_model.refresh()

        self._emit_event("controller.refresh.finished")
