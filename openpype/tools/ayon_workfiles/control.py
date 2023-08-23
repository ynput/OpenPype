import os
import ayon_api

from openpype.lib import Logger, emit_event
from openpype.lib.events import EventSystem
from openpype.settings import get_project_settings
from openpype.pipeline import Anatomy, registered_host
from openpype.pipeline.context_tools import change_current_context
from openpype.pipeline.workfile import create_workdir_extra_folders

from .abstract import AbstractWorkfileController
from .models import SelectionModel, EntitiesModel, WorkfilesModel


class ExpectedSelection:
    def __init__(self):
        self._folder_id = None
        self._task_name = None
        self._folder_selected = False
        self._task_selected = False

    def set_expected_selection(self, folder_id, task_name):
        self._folder_id = folder_id
        self._task_name = task_name
        self._folder_selected = False
        self._task_selected = False

    def get_expected_selection_data(self):
        return {
            "folder_id": self._folder_id,
            "task_name": self._task_name,
            "folder_selected": self._folder_selected,
            "task_selected": self._task_selected,
        }

    def expected_folder_selected(self, folder_id):
        if folder_id != self._folder_id:
            return False
        self._folder_selected = True
        return True

    def expected_task_selected(self, folder_id, task_name):
        if not self.expected_folder_selected(folder_id):
            return False

        if task_name != self._task_name:
            return False

        self._task_selected = True
        return True


class BaseWorkfileController(AbstractWorkfileController):
    def __init__(self, host=None):
        if host is None:
            host = registered_host()
        self._host = host

        self._project_anatomy = None
        self._project_settings = None
        self._event_system = None
        self._log = None

        self._current_project_name = None
        self._current_folder_name = None
        self._current_folder_id = None
        self._current_task_name = None

        # Expected selected folder and task
        self._expected_selection = ExpectedSelection()

        self._selection_model = SelectionModel(self)
        self._entities_model = EntitiesModel(self)
        self._workfiles_model = WorkfilesModel(self)

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger("WorkfilesUI")
        return self._log

    @property
    def project_settings(self):
        # TODO add cache timeout? It is refreshed on 'Refresh' button click.
        if self._project_settings is None:
            self._project_settings = get_project_settings(
                self.get_current_project_name())
        return self._project_settings

    @property
    def project_anatomy(self):
        # TODO add cache timeout? It is refreshed on 'Refresh' button click.
        if self._project_anatomy is None:
            self._project_anatomy = Anatomy(self.get_current_project_name())
        return self._project_anatomy

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

    def get_current_workfile(self):
        return self._host.get_current_workfile()

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
    def _trigger_expected_selection_changed(self):
        self._emit_event(
            "controller.expected_selection_changed",
            self._expected_selection.get_expected_selection_data(),
        )

    def set_expected_selection(self, folder_id, task_name):
        self._expected_selection.set_expected_selection(folder_id, task_name)
        self._trigger_expected_selection_changed()

    def expected_folder_selected(self, folder_id):
        if self._expected_selection.expected_folder_selected(folder_id):
            self._trigger_expected_selection_changed()

    def expected_task_selected(self, folder_id, task_name):
        if self._expected_selection.expected_task_selected(
            folder_id, task_name
        ):
            self._trigger_expected_selection_changed()

    def get_expected_selection_data(self):
        return self._expected_selection.get_expected_selection_data()

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

    def get_workarea_save_as_data(self, folder_id, task_id):
        return self._workfiles_model.get_workarea_save_as_data(
            folder_id, task_id)

    def fill_workarea_filepath(
        self,
        folder_id,
        task_id,
        extension,
        use_last_version,
        version,
        comment,
    ):
        return self._workfiles_model.fill_workarea_filepath(
            folder_id,
            task_id,
            extension,
            use_last_version,
            version,
            comment,
        )

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

        self._project_settings = None
        self._project_anatomy = None

        self._current_project_name = project_name
        self._current_folder_name = folder_name
        self._current_folder_id = folder_id
        self._current_task_name = task_name

        if not expected_folder_id:
            expected_folder_id = folder_id
            expected_task_name = task_name

        self._expected_selection.set_expected_selection(
            expected_folder_id, expected_task_name
        )

        self._entities_model.refresh()

        self._emit_event("controller.refresh.finished")

    # Controller actions
    def open_workfile(self, filepath):
        self._emit_event("controller.open_workfile.started")

        failed = False
        try:
            self._host.open_workfile(filepath)
        except Exception:
            failed = True
            # TODO add some visual feedback for user
            self.log.warning("Open of workfile failed", exc_info=True)

        self._emit_event(
            "controller.open_workfile.finished",
            {"failed": failed},
        )

    def save_as_workfile(self, *args, **kwargs):
        self._emit_event("controller.save_as.started")

        failed = False
        try:
            self._save_as_workfile(*args, **kwargs)
        except Exception:
            failed = True
            # TODO add some visual feedback for user
            self.log.warning("Save as failed", exc_info=True)

        self._emit_event(
            "controller.save_as.finished",
            {"failed": failed},
        )

    def _save_as_workfile(
        self,
        folder_id,
        task_id,
        workdir,
        filename,
        template_key,
    ):
        # Trigger before save event
        project_name = self.get_current_project_name()
        # TODO use entities model
        folder = ayon_api.get_folder_by_id(project_name, folder_id)
        task = ayon_api.get_task_by_id(project_name, task_id)
        task_name = task["name"]

        # QUESTION should the data be different for 'before' and 'after'?
        # NOTE keys should be OpenPype compatible
        event_data = {
            "project_name": project_name,
            "folder_id": folder_id,
            "asset_id": folder["id"],
            "asset_name": folder["name"],
            "task_id": task_id,
            "task_name": task_name,
            "host_name": self.get_host_name(),
            "filename": filename,
            "workdir_path": workdir,
        }
        emit_event("workfile.save.before", event_data, source="workfiles.tool")

        # Create workfiles root folder
        if not os.path.exists(workdir):
            self.log.debug("Initializing work directory: %s", workdir)
            os.makedirs(workdir)

        # Change context
        if (
            folder_id != self.get_current_folder_id()
            or task_name != self.get_current_task_name()
        ):
            change_current_context(
                folder,
                task["name"],
                template_key=template_key
            )

        # Save workfile
        filepath = os.path.join(workdir, filename)
        host = self._host
        if hasattr(host, "save_workfile"):
            host.save_workfile(filepath)
        else:
            host.save_file(filepath)

        # Create extra folders
        create_workdir_extra_folders(
            workdir,
            self.get_host_name(),
            task["taskType"],
            task_name,
            project_name
        )

        # Trigger after save events
        emit_event("workfile.save.after", event_data, source="workfiles.tool")
        self.refresh()
