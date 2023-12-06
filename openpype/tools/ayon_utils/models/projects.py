import contextlib
from abc import ABCMeta, abstractmethod

import ayon_api
import six

from openpype.style import get_default_entity_icon_color

from .cache import CacheItem

PROJECTS_MODEL_SENDER = "projects.model"


@six.add_metaclass(ABCMeta)
class AbstractHierarchyController:
    @abstractmethod
    def emit_event(self, topic, data, source):
        pass


class ProjectItem:
    """Item representing folder entity on a server.

    Folder can be a child of another folder or a project.

    Args:
        name (str): Project name.
        active (Union[str, None]): Parent folder id. If 'None' then project
            is parent.
    """

    def __init__(self, name, active, is_library, icon=None):
        self.name = name
        self.active = active
        self.is_library = is_library
        if icon is None:
            icon = {
                "type": "awesome-font",
                "name": "fa.book" if is_library else "fa.map",
                "color": get_default_entity_icon_color(),
            }
        self.icon = icon

    def to_data(self):
        """Converts folder item to data.

        Returns:
            dict[str, Any]: Folder item data.
        """

        return {
            "name": self.name,
            "active": self.active,
            "is_library": self.is_library,
            "icon": self.icon,
        }

    @classmethod
    def from_data(cls, data):
        """Re-creates folder item from data.

        Args:
            data (dict[str, Any]): Folder item data.

        Returns:
            FolderItem: Folder item.
        """

        return cls(**data)


def _get_project_items_from_entitiy(projects):
    """

    Args:
        projects (list[dict[str, Any]]): List of projects.

    Returns:
        ProjectItem: Project item.
    """

    return [
        ProjectItem(project["name"], project["active"], project["library"])
        for project in projects
    ]


class ProjectsModel(object):
    def __init__(self, controller):
        self._projects_cache = CacheItem(default_factory=list)
        self._project_items_by_name = {}
        self._projects_by_name = {}

        self._is_refreshing = False
        self._controller = controller

    def reset(self):
        self._projects_cache.reset()
        self._project_items_by_name = {}
        self._projects_by_name = {}

    def refresh(self):
        self._refresh_projects_cache()

    def get_project_items(self, sender):
        """

        Args:
            sender (str): Name of sender who asked for items.

        Returns:
            Union[list[ProjectItem], None]: List of project items, or None
                if model is refreshing.
        """

        if not self._projects_cache.is_valid:
            return self._refresh_projects_cache(sender)
        return self._projects_cache.get_data()

    def get_project_entity(self, project_name):
        if project_name not in self._projects_by_name:
            entity = None
            if project_name:
                entity = ayon_api.get_project(project_name)
            self._projects_by_name[project_name] = entity
        return self._projects_by_name[project_name]

    @contextlib.contextmanager
    def _project_refresh_event_manager(self, sender):
        self._is_refreshing = True
        self._controller.emit_event(
            "projects.refresh.started",
            {"sender": sender},
            PROJECTS_MODEL_SENDER
        )
        try:
            yield

        finally:
            self._controller.emit_event(
                "projects.refresh.finished",
                {"sender": sender},
                PROJECTS_MODEL_SENDER
            )
            self._is_refreshing = False

    def _refresh_projects_cache(self, sender=None):
        if self._is_refreshing:
            return None

        with self._project_refresh_event_manager(sender):
            project_items = self._query_projects()
            self._projects_cache.update_data(project_items)
        return self._projects_cache.get_data()

    def _query_projects(self):
        projects = ayon_api.get_projects(fields=["name", "active", "library"])
        return _get_project_items_from_entitiy(projects)
