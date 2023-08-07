import os
import copy

from openpype.client import get_workfile_info
from openpype.client.operations import (
    OperationsSession,
    new_workfile_info_doc,
    prepare_workfile_info_update_data,
)
from openpype.pipeline.template_data import (
    get_template_data,
    get_asset_template_data,
)


class FileItem:
    def __init__(self, dirpath, filename, modified):
        self.filename = filename
        self.dirpath = dirpath
        self.modified = modified

    @classmethod
    def from_dir(cls, dirpath, extensions):
        output = []
        if not dirpath or not os.path.exists(dirpath):
            return output

        for filename in os.listdir(dirpath):
            ext = os.path.splitext(filename)[-1]
            if ext.lower() not in extensions:
                continue
            output.append(cls(
                dirpath,
                filename,
                os.path.getmtime(os.path.join(dirpath, filename))
            ))

        return output


class WorkareaModel:
    def __init__(self, control):
        self._control = control
        self._extensions = control.get_workfile_extensions()
        self._base_data = None
        self._fill_data_by_folder_id = {}
        self._task_data_by_folder_id = {}

    def reset(self):
        self._base_data = None
        self._fill_data_by_folder_id = {}
        self._task_data_by_folder_id = {}

    def _get_base_data(self):
        if self._base_data is None:
            self._base_data = get_template_data(
                self._control.project_name)
        return copy.deepcopy(self._base_data)

    def _get_folder_data(self, folder_id):
        fill_data = self._fill_data_by_folder_id.get(folder_id)
        if fill_data is None:
            fill_data = get_asset_template_data(
                folder_id, self._control.project_name)
            self._fill_data_by_folder_id[folder_id] = fill_data
        return copy.deepcopy(fill_data)

    def _get_task_data(self, folder_id, task_name):
        pass

    def _prepare_fill_data(self, folder_id, task_name):
        if not folder_id or not task_name:
            return {}

        base_data = self._get_base_data()

        fill_data = self._fill_data_by_folder_id.get(folder_id)
        if fill_data is None:
            fill_data = get_asset_template_data(
                folder_id, self._control.project_name)
            self._fill_data_by_folder_id[folder_id] = fill_data

    def get_file_items(self, folder_id, task_name):
        # TODO finish implementation
        if not folder_id or not task_name:
            return []

        return []


class WorkfilesModel:
    """Workfiles model.

    This model requires 'anatomy' property on controller that returns
        'Anatomy' object for current project.
    """

    def __init__(self, control):
        self._control = control
        self._cache = {}

    def get_workfile_info(self, folder_id, task_name, filepath):
        if not folder_id or not task_name or not filepath:
            return None

        # TODO add caching mechanism
        identifier = "_".join([folder_id, task_name, filepath])
        info = self._cache.get(identifier)
        if not info:
            info = get_workfile_info(
                self._control.get_current_project_name(),
                folder_id,
                task_name,
                filepath
            )
            self._cache[identifier] = info
        return info

    def save_workdile_data(self, folder_id, task_name, filepath, note):
        workfile_doc = self.get_workfile_info(folder_id, task_name, filepath)
        if not workfile_doc:
            workfile_doc = self._create_workfile_doc(filepath)

        new_workfile_doc = copy.deepcopy(workfile_doc)
        new_workfile_doc.setdefault("data", {})

        new_workfile_doc["data"]["note"] = note
        update_data = prepare_workfile_info_update_data(
            workfile_doc, new_workfile_doc
        )
        if not update_data:
            return

        project_name = self._control.get_current_project_name()
        session = OperationsSession()
        session.update_entity(
            project_name, "workfile", workfile_doc["_id"], update_data
        )
        session.commit()

    def _get_current_workfile_doc(self, filepath=None):
        if filepath is None:
            filepath = self._control.get_selected_workfile_path()
        folder_id = self._control.get_selected_folder_id()
        task_name = self._control.get_selected_task_name()
        if not task_name or not folder_id or not filepath:
            return

        filename = os.path.split(filepath)[1]
        project_name = self._control.get_current_project_name()
        return get_workfile_info(
            project_name, folder_id, task_name, filename
        )

    def _create_workfile_doc(self, filepath):
        workfile_doc = self._get_current_workfile_doc(filepath)
        if workfile_doc:
            return workfile_doc

        workdir, filename = os.path.split(filepath)

        project_name = self._control.get_current_project_name()
        folder_id = self._control.get_selected_folder_id()
        task_name = self._control.get_selected_task_name()
        anatomy = self._control.anatomy

        success, rootless_dir = anatomy.find_root_template_from_path(workdir)
        filepath = "/".join([
            os.path.normpath(rootless_dir).replace("\\", "/"),
            filename
        ])

        workfile_doc = new_workfile_info_doc(
            filename, folder_id, task_name, [filepath]
        )
        session = OperationsSession()
        session.create_entity(project_name, "workfile", workfile_doc)
        session.commit()
        return workfile_doc
