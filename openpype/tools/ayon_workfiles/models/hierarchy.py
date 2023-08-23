"""Hierarchy model that handles folders and tasks.

The model can be extracted for common usage. In that case it will be required
to add more handling of project name changes.
"""

import time
import collections
import contextlib

import ayon_api

from openpype.style import get_default_entity_icon_color


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
        self._label = None

    @property
    def id(self):
        return self.task_id

    @property
    def label(self):
        if self._label is None:
            self._label = "{} ({})".format(self.name, self.task_type)
        return self._label

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

    def __init__(self, controller):
        folders_cache = CacheItem()
        folders_cache.set_invalid({})
        self._folders_cache = folders_cache
        self._folder_id_by_path = {}
        self._tasks_cache = {}

        self._folders_refreshing = False
        self._tasks_refreshing = set()
        self._controller = controller

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
        self._controller.emit_event(
            "folders.refresh.started",
            {"project_name": project_name},
            self.event_source
        )
        try:
            yield

        finally:
            self._controller.emit_event(
                "folders.refresh.finished",
                {"project_name": project_name},
                self.event_source
            )
            self._folders_refreshing = False

    @contextlib.contextmanager
    def _task_refresh_event_manager(self, project_name, folder_id):
        self._tasks_refreshing.add(folder_id)
        self._controller.emit_event(
            "tasks.refresh.started",
            {"project_name": project_name, "folder_id": folder_id},
            self.event_source
        )
        try:
            yield

        finally:
            self._controller.emit_event(
                "tasks.refresh.finished",
                {"project_name": project_name, "folder_id": folder_id},
                self.event_source
            )
            self._tasks_refreshing.discard(folder_id)

    def _refresh_folders_cache(self):
        if self._folders_refreshing:
            return
        project_name = self._controller.get_current_project_name()
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

        project_name = self._controller.get_current_project_name()
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
