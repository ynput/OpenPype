"""Hierarchy model that handles folders and tasks.

The model can be extracted for common usage. In that case it will be required
to add more handling of project name changes.
"""

import time
import collections
import contextlib

import ayon_api

from openpype.tools.ayon_workfiles.abstract import (
    FolderItem,
    TaskItem,
)


def _get_task_items_from_tasks(tasks):
    """

    Returns:
        TaskItem: Task item.
    """

    output = []
    for task in tasks:
        folder_id = task["folderId"]
        output.append(TaskItem(
            task["id"],
            task["name"],
            task["type"],
            folder_id,
            None,
            None
        ))
    return output


def _get_folder_item_from_hierarchy_item(item):
    return FolderItem(
        item["id"],
        item["parentId"],
        item["name"],
        item["label"],
        None,
        None,
    )


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
        project_cache = CacheItem()
        project_cache.set_invalid({})
        folders_cache = CacheItem()
        folders_cache.set_invalid({})
        self._project_cache = project_cache
        self._folders_cache = folders_cache
        self._tasks_cache = {}

        self._folders_by_id = {}
        self._tasks_by_id = {}

        self._folders_refreshing = False
        self._tasks_refreshing = set()
        self._controller = controller

    def reset(self):
        self._project_cache.set_invalid({})
        self._folders_cache.set_invalid({})
        self._tasks_cache = {}

        self._folders_by_id = {}
        self._tasks_by_id = {}

    def refresh(self):
        self._refresh_folders_cache()

    def get_project_entity(self):
        if not self._project_cache.is_valid:
            project_name = self._controller.get_current_project_name()
            project_entity = ayon_api.get_project(project_name)
            self._project_cache.update_data(project_entity)
        return self._project_cache.get_data()

    def get_folder_items(self, sender):
        if not self._folders_cache.is_valid:
            self._refresh_folders_cache(sender)
        return self._folders_cache.get_data()

    def get_tasks_items(self, folder_id, sender):
        if not folder_id:
            return []

        task_cache = self._tasks_cache.get(folder_id)
        if task_cache is None or not task_cache.is_valid:
            self._refresh_tasks_cache(folder_id, sender)
            task_cache = self._tasks_cache.get(folder_id)
        return task_cache.get_data()

    def get_folder_entity(self, folder_id):
        if folder_id not in self._folders_by_id:
            entity = None
            if folder_id:
                project_name = self._controller.get_current_project_name()
                entity = ayon_api.get_folder_by_id(project_name, folder_id)
            self._folders_by_id[folder_id] = entity
        return self._folders_by_id[folder_id]

    def get_task_entity(self, task_id):
        if task_id not in self._tasks_by_id:
            entity = None
            if task_id:
                project_name = self._controller.get_current_project_name()
                entity = ayon_api.get_task_by_id(project_name, task_id)
            self._tasks_by_id[task_id] = entity
        return self._tasks_by_id[task_id]

    @contextlib.contextmanager
    def _folder_refresh_event_manager(self, project_name, sender):
        self._folders_refreshing = True
        self._controller.emit_event(
            "folders.refresh.started",
            {"project_name": project_name, "sender": sender},
            self.event_source
        )
        try:
            yield

        finally:
            self._controller.emit_event(
                "folders.refresh.finished",
                {"project_name": project_name, "sender": sender},
                self.event_source
            )
            self._folders_refreshing = False

    @contextlib.contextmanager
    def _task_refresh_event_manager(
        self, project_name, folder_id, sender
    ):
        self._tasks_refreshing.add(folder_id)
        self._controller.emit_event(
            "tasks.refresh.started",
            {
                "project_name": project_name,
                "folder_id": folder_id,
                "sender": sender,
            },
            self.event_source
        )
        try:
            yield

        finally:
            self._controller.emit_event(
                "tasks.refresh.finished",
                {
                    "project_name": project_name,
                    "folder_id": folder_id,
                    "sender": sender,
                },
                self.event_source
            )
            self._tasks_refreshing.discard(folder_id)

    def _refresh_folders_cache(self, sender=None):
        if self._folders_refreshing:
            return
        project_name = self._controller.get_current_project_name()
        with self._folder_refresh_event_manager(project_name, sender):
            folder_items = self._query_folders(project_name)
            self._folders_cache.update_data(folder_items)

    def _query_folders(self, project_name):
        hierarchy = ayon_api.get_folders_hierarchy(project_name)

        folder_items = {}
        hierachy_queue = collections.deque(hierarchy["hierarchy"])
        while hierachy_queue:
            item = hierachy_queue.popleft()
            folder_item = _get_folder_item_from_hierarchy_item(item)
            folder_items[folder_item.entity_id] = folder_item
            hierachy_queue.extend(item["children"] or [])
        return folder_items

    def _refresh_tasks_cache(self, folder_id, sender=None):
        if folder_id in self._tasks_refreshing:
            return

        project_name = self._controller.get_current_project_name()
        with self._task_refresh_event_manager(
            project_name, folder_id, sender
        ):
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
        return _get_task_items_from_tasks(tasks)
