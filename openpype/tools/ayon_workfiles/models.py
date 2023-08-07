import os
import time
import copy
import contextlib
import collections

import ayon_api

from openpype.style import get_default_entity_icon_color
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


class FolderItem:
    """

    Args:
        entity_id (str): Folder id.
        parent_id (Union[str, None]): Parent folder id. If 'None' then project
            is parent.
        name (str): Name of folder.
        label (str): Folder label.
        icon_name (str): Name of icon from font awesome.
        icon_color (str): Hex color string that will be used for icon.
    """

    def __init__(
        self, entity_id, parent_id, name, label, icon_name, icon_color
    ):
        self.entity_id = entity_id
        self.parent_id = parent_id
        self.name = name
        self.icon_name = icon_name or "fa.folder"
        self.icon_color = icon_color or get_default_entity_icon_color()
        self.label = label or name

    def to_data(self):
        return {
            "entity_id": self.entity_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "label": self.label,
            "icon_name": self.icon_name,
            "icon_color": self.icon_color,
        }

    @classmethod
    def from_data(cls, data):
        return cls(**data)

    @classmethod
    def from_hierarchy_item(cls, item):
        return cls(
            item["id"],
            item["parentId"],
            item["name"],
            item["label"],
            None,
            None,
        )


class TaskItem:
    """

    Args:
        task_id (str): Task id.
        name (str): Name of task.
        task_type (str): Type of task.
        parent_id (str): Parent folder id.
        icon_name (str): Name of icon from font awesome.
        icon_color (str): Hex color string that will be used for icon.
    """

    def __init__(
        self, task_id, name, task_type, parent_id, icon_name, icon_color
    ):
        self.task_id = task_id
        self.name = name
        self.task_type = task_type
        self.parent_id = parent_id
        self.icon_name = icon_name or "fa.male"
        self.icon_color = icon_color or get_default_entity_icon_color()

    @property
    def id(self):
        return self.task_id

    def to_data(self):
        return {
            "task_id": self.task_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "task_type": self.task_type,
            "icon_name": self.icon_name,
            "icon_color": self.icon_color,
        }

    @classmethod
    def from_data(cls, data):
        return cls(**data)

    @classmethod
    def from_tasks(cls, tasks):
        """

        Returns:
            TaskItem: Task item.
        """

        output = []
        for task in tasks:
            folder_id = task["folderId"]
            output.append(cls(
                task["id"],
                task["name"],
                task["type"],
                folder_id,
                None,
                None
            ))
        return output


class CacheItem:
    def __init__(self, lifetime=120):
        self._lifetime = lifetime
        self._last_update = None
        self._data = None

    @property
    def is_valid(self):
        if self._last_update is None:
            return False

        return (time.time() - self._last_update) < self._lifetime

    def set_invalid(self, data=None):
        self._last_update = None
        self._data = data

    def get_data(self):
        return self._data

    def update_data(self, data):
        self._data = data
        self._last_update = time.time()


class EntitiesModel(object):
    event_source = "entities.model"

    def __init__(self, control):
        folders_cache = CacheItem()
        folders_cache.set_invalid({})
        self._folders_cache = folders_cache
        self._folder_id_by_path = {}
        self._tasks_cache = {}

        self._folders_refreshing = False
        self._tasks_refreshing = set()
        self._control = control

    def reset(self):
        self._folders_cache.set_invalid({})
        self._tasks_cache = {}
        self._folder_id_by_path = {}

    def refresh(self):
        self._refresh_folders_cache()

    def get_folder_id(self, folder_path):
        return self._folder_id_by_path.get(folder_path)

    def get_folder_path(self, folder_id):
        folder_items = self._folders_cache.get_data()
        return folder_items.get(folder_id)

    def get_folder_items(self):
        if not self._folders_cache.is_valid:
            self._refresh_folders_cache()
            return None
        return self._folders_cache.get_data()

    def get_tasks_items(self, folder_id):
        if not folder_id:
            return []

        task_cache = self._tasks_cache.get(folder_id)
        if task_cache is None or not task_cache.is_valid:
            self._refresh_tasks_cache(folder_id)
            return None
        return task_cache.get_data()

    @contextlib.contextmanager
    def _folder_refresh_event_manager(self, project_name):
        self._folders_refreshing = True
        self._control.emit_event(
            "folders.refresh.started",
            {"project_name": project_name},
            self.event_source
        )
        try:
            yield

        finally:
            self._control.emit_event(
                "folders.refresh.finished",
                {"project_name": project_name},
                self.event_source
            )
            self._folders_refreshing = False

    @contextlib.contextmanager
    def _task_refresh_event_manager(self, project_name, folder_id):
        self._tasks_refreshing.add(folder_id)
        self._control.emit_event(
            "tasks.refresh.started",
            {"project_name": project_name, "folder_id": folder_id},
            self.event_source
        )
        try:
            yield

        finally:
            self._control.emit_event(
                "tasks.refresh.finished",
                {"project_name": project_name, "folder_id": folder_id},
                self.event_source
            )
            self._tasks_refreshing.discard(folder_id)

    def _refresh_folders_cache(self):
        if self._folders_refreshing:
            return
        project_name = self._control.get_current_project_name()
        with self._folder_refresh_event_manager(project_name):
            folder_items = self._query_folders(project_name)
            self._folders_cache.update_data(folder_items)

    def _query_folders(self, project_name):
        hierarchy = ayon_api.get_folders_hierarchy(project_name)

        folder_items = {}
        hierachy_queue = collections.deque(hierarchy["hierarchy"])
        while hierachy_queue:
            item = hierachy_queue.popleft()
            folder_item = FolderItem.from_hierarchy_item(item)
            folder_items[folder_item.entity_id] = folder_item
            hierachy_queue.extend(item["children"] or [])
        return folder_items

    def _refresh_tasks_cache(self, folder_id):
        if folder_id in self._tasks_refreshing:
            return

        project_name = self._control.get_current_project_name()
        with self._task_refresh_event_manager(project_name, folder_id):
            cache_item = self._tasks_cache.get(folder_id)
            if cache_item is None:
                cache_item = CacheItem()
                self._tasks_cache[folder_id] = cache_item

            task_items = self._query_tasks(project_name, folder_id)
            cache_item.update_data(task_items)

    def _query_tasks(self, project_name, folder_id):
        tasks = list(ayon_api.get_tasks(
            project_name,
            folder_ids=[folder_id],
            fields={"id", "name", "label", "folderId", "type"}
        ))
        return TaskItem.from_tasks(tasks)


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


class SelectionModel(object):
    """Model handling selection changes.

    Triggering events:
    - "selection.folder.changed"
    - "selection.task.changed"
    - "selection.path.changed"
    - "selection.representation.changed"
    """

    event_source = "selection.model"

    def __init__(self, control):
        self._control = control

        self._folder_id = None
        self._task_name = None
        self._task_id = None
        self._workfile_path = None
        self._representation_id = None

    def get_selected_folder_id(self):
        return self._folder_id

    def set_selected_folder(self, folder_id):
        if folder_id == self._folder_id:
            return

        self._folder_id = folder_id
        self._control.emit_event(
            "selection.folder.changed",
            {"folder_id": folder_id},
            self.event_source
        )

    def get_selected_task_name(self):
        return self._task_name

    def set_selected_task(self, folder_id, task_id, task_name):
        if folder_id != self._folder_id:
            self.set_selected_folder(folder_id)

        if task_id == self._task_id:
            return

        self._task_name = task_name
        self._task_id = task_id
        self._control.emit_event(
            "selection.task.changed",
            {
                "folder_id": folder_id,
                "task_name": task_name,
                "task_id": task_id
            },
            self.event_source
        )

    def get_selected_workfile_path(self):
        return self._workfile_path

    def set_selected_workfile_path(self, path):
        if path == self._workfile_path:
            return

        self._workfile_path = path
        self._control.emit_event(
            "selection.path.changed",
            {"path": path},
            self.event_source
        )

    def get_selected_representation_id(self):
        return self._representation_id

    def set_selected_representation_id(self, representation_id):
        if representation_id == self._representation_id:
            return
        self._representation_id = representation_id
        self._control.emit_event(
            "selection.representation.changed",
            {"representation_id": representation_id},
            self.event_source
        )


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
