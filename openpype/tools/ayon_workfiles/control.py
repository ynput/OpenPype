import sys

import six
import ayon_api

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
        self._current_folder_name = None
        self._current_folder_id = None
        self._current_task_name = None

        # Expected selected folder and task
        self._expected_folder_id = None
        self._expected_task_name = None

        self._selection_model = SelectionModel(self)
        self._entities_model = EntitiesModel(self)
        self._workfiles_model = WorkfilesModel(self)

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger("WorkfilesUI")
        return self._log

    @property
    def project_anatomy(self):
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
    def get_host_name(self):
        return self._host.name

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

    def get_selected_task_id(self):
        return self._selection_model.get_selected_task_id()

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

    # Expected selection
    # - expected selection is used to restore selection after refresh
    #   or when current context should be used
    def set_expected_selection(self, folder_id, task_name):
        self._expected_folder_id = folder_id
        self._expected_task_name = task_name
        self._emit_event(
            "controller.expected_selection_changed",
            {"folder_id": folder_id, "task_name": task_name},
        )

    def set_expected_folder_id(self, folder_id):
        self.set_expected_selection(folder_id, self._expected_task_name)

    def set_expected_task_name(self, task_name):
        self.set_expected_selection(self._expected_folder_id, task_name)

    def get_expected_folder_id(self):
        return self._expected_folder_id

    def get_expected_task_name(self):
        return self._expected_task_name

    def go_to_current_context(self):
        self.set_expected_selection(
            self._current_folder_id, self._current_task_name
        )

    # Model functions
    def get_folder_items(self):
        return self._entities_model.get_folder_items()

    def get_task_items(self, folder_id):
        return self._entities_model.get_tasks_items(folder_id)

    def get_workarea_dir_by_context(self, folder_id, task_id):
        return self._workfiles_model.get_workarea_dir_by_context(
            folder_id, task_id)

    def get_workarea_file_items(self, folder_id, task_id):
        return self._workfiles_model.get_workarea_file_items(
            folder_id, task_id)

    def get_published_file_items(self, folder_id):
        return self._workfiles_model.get_published_file_items(folder_id)

    def get_workfile_info(self, folder_id, task_id, filepath):
        return self._workfiles_model.get_workfile_info(
            folder_id, task_id, filepath
        )

    def save_workfile_info(self, folder_id, task_id, filepath, note):
        return self._workfiles_model.save_workfile_info(
            folder_id, task_id, filepath, note
        )

    def refresh(self):
        expected_folder_id = self.get_selected_folder_id()
        expected_task_name = self.get_selected_task_name()

        self._emit_event("controller.refresh.started")

        context = self._host.get_current_context()

        project_name = context["project_name"]
        folder_name = context["asset_name"]
        task_name = context["task_name"]
        folder_id = None
        if folder_name:
            folder = ayon_api.get_folder_by_name(project_name, folder_name)
            if folder:
                folder_id = folder["id"]

        self._current_project_name = project_name
        self._current_folder_name = folder_name
        self._current_folder_id = folder_id
        self._current_task_name = task_name

        if not expected_folder_id:
            expected_folder_id = folder_id
            expected_task_name = task_name

        self._expected_folder_id = expected_folder_id
        self._expected_task_name = expected_task_name

        self._entities_model.refresh()

        self._emit_event("controller.refresh.finished")

    # Controller actions
    def open_workfile(self, filepath):
        self._emit_event("controller.open_workfile.started")

        exc_cls = exc = tb = None
        failed = False
        try:
            self._host.open_workfile(filepath)
        except Exception:
            failed = True
            exc_cls, exc, tb = sys.exc_info()

        self._emit_event(
            "controller.open_workfile.finished",
            {"failed": failed},
        )
        # TODO reraise is probably not good idea
        if failed:
            six.reraise(exc_cls, exc, tb)
