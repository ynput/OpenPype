import os
import shutil

import ayon_api

from openpype.host import IWorkfileHost
from openpype.lib import Logger, emit_event
from openpype.lib.events import QueuedEventSystem
from openpype.settings import get_project_settings
from openpype.pipeline import Anatomy, registered_host
from openpype.pipeline.context_tools import change_current_context
from openpype.pipeline.workfile import create_workdir_extra_folders

from .abstract import (
    AbstractWorkfilesFrontend,
    AbstractWorkfilesBackend,
)
from .models import SelectionModel, EntitiesModel, WorkfilesModel


class ExpectedSelection:
    def __init__(self):
        self._folder_id = None
        self._task_name = None
        self._workfile_name = None
        self._representation_id = None
        self._folder_selected = True
        self._task_selected = True
        self._workfile_name_selected = True
        self._representation_id_selected = True

    def set_expected_selection(
        self,
        folder_id,
        task_name,
        workfile_name=None,
        representation_id=None
    ):
        self._folder_id = folder_id
        self._task_name = task_name
        self._workfile_name = workfile_name
        self._representation_id = representation_id
        self._folder_selected = False
        self._task_selected = False
        self._workfile_name_selected = workfile_name is None
        self._representation_id_selected = representation_id is None

    def get_expected_selection_data(self):
        return {
            "folder_id": self._folder_id,
            "task_name": self._task_name,
            "workfile_name": self._workfile_name,
            "representation_id": self._representation_id,
            "folder_selected": self._folder_selected,
            "task_selected": self._task_selected,
            "workfile_name_selected": self._workfile_name_selected,
            "representation_id_selected": self._representation_id_selected,
        }

    def is_expected_folder_selected(self, folder_id):
        return folder_id == self._folder_id and self._folder_selected

    def is_expected_task_selected(self, folder_id, task_name):
        if not self.is_expected_folder_selected(folder_id):
            return False
        return task_name == self._task_name and self._task_selected

    def expected_folder_selected(self, folder_id):
        if folder_id != self._folder_id:
            return False
        self._folder_selected = True
        return True

    def expected_task_selected(self, folder_id, task_name):
        if not self.is_expected_folder_selected(folder_id):
            return False

        if task_name != self._task_name:
            return False

        self._task_selected = True
        return True

    def expected_workfile_selected(self, folder_id, task_name, workfile_name):
        if not self.is_expected_task_selected(folder_id, task_name):
            return False

        if workfile_name != self._workfile_name:
            return False
        self._workfile_name_selected = True
        return True

    def expected_representation_selected(
        self, folder_id, task_name, representation_id
    ):
        if not self.is_expected_task_selected(folder_id, task_name):
            return False
        if representation_id != self._representation_id:
            return False
        self._representation_id_selected = True
        return True


class BaseWorkfileController(
    AbstractWorkfilesFrontend, AbstractWorkfilesBackend
):
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
        self._expected_selection = self._create_expected_selection_obj()

        self._selection_model = self._create_selection_model()
        self._entities_model = self._create_entities_model()
        self._workfiles_model = self._create_workfiles_model()

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger("WorkfilesUI")
        return self._log

    def _create_expected_selection_obj(self):
        return ExpectedSelection()

    def _create_selection_model(self):
        return SelectionModel(self)

    def _create_entities_model(self):
        return EntitiesModel(self)

    def _create_workfiles_model(self):
        return WorkfilesModel(self)

    @property
    def event_system(self):
        """Inner event system for workfiles tool controller.

        Is used for communication with UI. Event system is created on demand.

        Returns:
            QueuedEventSystem: Event system which can trigger callbacks for topics.
        """

        if self._event_system is None:
            self._event_system = QueuedEventSystem()
        return self._event_system

    # ----------------------------------------------------
    # Implementation of methods required for backend logic
    # ----------------------------------------------------
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

    def get_folder_entity(self, folder_id):
        return self._entities_model.get_folder_entity(folder_id)

    def get_task_entity(self, task_id):
        return self._entities_model.get_task_entity(task_id)

    # ---------------------------------
    # Implementation of abstract methods
    # ---------------------------------
    def emit_event(self, topic, data=None, source=None):
        """Use implemented event system to trigger event."""

        if data is None:
            data = {}
        self.event_system.emit(topic, data, source)

    def register_event_callback(self, topic, callback):
        self.event_system.add_callback(topic, callback)

    # Host information
    def get_workfile_extensions(self):
        return self._host.get_workfile_extensions()

    def has_unsaved_changes(self):
        host = self._host
        if isinstance(host, IWorkfileHost):
            return host.workfile_has_unsaved_changes()
        return host.has_unsaved_changes()

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

    def set_expected_selection(
        self,
        folder_id,
        task_name,
        workfile_name=None,
        representation_id=None
    ):
        self._expected_selection.set_expected_selection(
            folder_id, task_name, workfile_name, representation_id
        )
        self._trigger_expected_selection_changed()

    def expected_folder_selected(self, folder_id):
        if self._expected_selection.expected_folder_selected(folder_id):
            self._trigger_expected_selection_changed()

    def expected_task_selected(self, folder_id, task_name):
        if self._expected_selection.expected_task_selected(
            folder_id, task_name
        ):
            self._trigger_expected_selection_changed()

    def expected_workfile_selected(self, folder_id, task_name, workfile_name):
        if self._expected_selection.expected_workfile_selected(
            folder_id, task_name, workfile_name
        ):
            self._trigger_expected_selection_changed()

    def expected_representation_selected(
        self, folder_id, task_name, representation_id
    ):
        if self._expected_selection.expected_representation_selected(
            folder_id, task_name, representation_id
        ):
            self._trigger_expected_selection_changed()

    def get_expected_selection_data(self):
        return self._expected_selection.get_expected_selection_data()

    def go_to_current_context(self):
        self.set_expected_selection(
            self._current_folder_id, self._current_task_name
        )

    # Model functions
    def get_folder_items(self, sender):
        return self._entities_model.get_folder_items(sender)

    def get_task_items(self, folder_id, sender):
        return self._entities_model.get_tasks_items(folder_id, sender)

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

    def get_published_file_items(self, folder_id, task_id):
        task_name = None
        if task_id:
            task = self.get_task_entity(task_id)
            task_name = task.get("name")

        return self._workfiles_model.get_published_file_items(
            folder_id, task_name)

    def get_workfile_info(self, folder_id, task_id, filepath):
        return self._workfiles_model.get_workfile_info(
            folder_id, task_id, filepath
        )

    def save_workfile_info(self, folder_id, task_id, filepath, note):
        self._workfiles_model.save_workfile_info(
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
        self._emit_event("open_workfile.started")

        failed = False
        try:
            self._host.open_workfile(filepath)
        except Exception:
            failed = True
            # TODO add some visual feedback for user
            self.log.warning("Open of workfile failed", exc_info=True)

        self._emit_event(
            "open_workfile.finished",
            {"failed": failed},
        )

    def save_current_workfile(self):
        host = self._host
        if isinstance(host, IWorkfileHost):
            current_file = host.get_current_workfile()
            host.save_workfile(current_file)
        else:
            current_file = host.current_file()
            host.save_file(current_file)

    def save_as_workfile(
        self,
        folder_id,
        task_id,
        workdir,
        filename,
        template_key,
    ):
        self._emit_event("save_as.started")

        failed = False
        try:
            self._save_as_workfile(
                folder_id,
                task_id,
                workdir,
                filename,
                template_key,
            )
        except Exception:
            failed = True
            # TODO add some visual feedback for user
            self.log.warning("Save as failed", exc_info=True)

        self._emit_event(
            "save_as.finished",
            {"failed": failed},
        )

    def copy_workfile_representation(
        self,
        representation_id,
        representation_filepath,
        folder_id,
        task_id,
        workdir,
        filename,
        template_key,
    ):
        self._emit_event("copy_representation.started")

        failed = False
        try:
            self._save_as_workfile(
                folder_id,
                task_id,
                workdir,
                filename,
                template_key,
            )
        except Exception:
            failed = True
            # TODO add some visual feedback for user
            self.log.warning(
                "Copy of workfile representation failed", exc_info=True
            )

        self._emit_event(
            "copy_representation.finished",
            {"failed": failed},
        )

    def _emit_event(self, topic, data=None):
        self.emit_event(topic, data, "controller")

    # Expected selection
    # - expected selection is used to restore selection after refresh
    #   or when current context should be used
    def _trigger_expected_selection_changed(self):
        self._emit_event(
            "expected_selection_changed",
            self._expected_selection.get_expected_selection_data(),
        )

    def _save_as_workfile(
        self,
        folder_id,
        task_id,
        workdir,
        filename,
        template_key,
        src_filepath=None,
    ):
        # Trigger before save event
        project_name = self.get_current_project_name()
        folder = self.get_folder_entity(folder_id)
        task = self.get_task_entity(task_id)
        task_name = task["name"]

        # QUESTION should the data be different for 'before' and 'after'?
        # NOTE keys should be OpenPype compatible
        event_data = {
            "project_name": project_name,
            "folder_id": folder_id,
            "asset_id": folder_id,
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
        dst_filepath = os.path.join(workdir, filename)
        host = self._host
        if src_filepath:
            shutil.copyfile(src_filepath, dst_filepath)
            if isinstance(host, IWorkfileHost):
                host.open_workfile(dst_filepath)
            else:
                host.open_file(dst_filepath)
        else:
            if isinstance(host, IWorkfileHost):
                host.save_workfile(dst_filepath)
            else:
                host.save_file(dst_filepath)

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
