import logging

import ayon_api

from openpype.lib.events import QueuedEventSystem
from openpype.pipeline import Anatomy, get_current_context
from openpype.host import ILoadHost
from openpype.tools.ayon_utils.models import (
    ProjectsModel,
    HierarchyModel,
    NestedCacheItem,
    CacheItem,
)

from .abstract import AbstractController
from .models import SelectionModel, ProductsModel, LoaderActionsModel


class LoaderController(AbstractController):
    """

    Args:
        host (Optional[AbstractHost]): Host object. Defaults to None.
    """

    def __init__(self, host=None):
        self._log = None
        self._host = host

        self._event_system = self._create_event_system()

        self._project_anatomy_cache = NestedCacheItem(levels=1)
        self._loaded_products_cache = CacheItem(
            default_factory=set, lifetime=60)

        self._selection_model = SelectionModel(self)
        self._projects_model = ProjectsModel(self)
        self._hierarchy_model = HierarchyModel(self)
        self._products_model = ProductsModel(self)
        self._loader_actions_model = LoaderActionsModel(self)

    @property
    def log(self):
        if self._log is None:
            self._log = logging.getLogger(self.__class__.__name__)
        return self._log

    # ---------------------------------
    # Implementation of abstract methods
    # ---------------------------------
    # Events system
    def emit_event(self, topic, data=None, source=None):
        """Use implemented event system to trigger event."""

        if data is None:
            data = {}
        self._event_system.emit(topic, data, source)

    def register_event_callback(self, topic, callback):
        self._event_system.add_callback(topic, callback)

    def reset(self):
        self._emit_event("controller.reset.started")

        self._project_anatomy_cache.reset()
        self._loaded_products_cache.reset()

        self._products_model.reset()
        self._hierarchy_model.reset()
        self._loader_actions_model.reset()
        self._projects_model.refresh()

        self._emit_event("controller.reset.finished")

    # Entity model wrappers
    def get_project_items(self, sender=None):
        return self._projects_model.get_project_items(sender)

    def get_folder_items(self, project_name, sender=None):
        return self._hierarchy_model.get_folder_items(project_name, sender)

    def get_product_items(self, project_name, folder_ids, sender=None):
        return self._products_model.get_product_items(
            project_name, folder_ids, sender)

    def get_product_item(self, project_name, product_id):
        return self._products_model.get_product_item(
            project_name, product_id
        )

    def get_product_type_items(self, project_name):
        return self._products_model.get_product_type_items(project_name)

    def get_representation_items(
        self, project_name, version_ids, sender=None
    ):
        return self._products_model.get_repre_items(
            project_name, version_ids, sender
        )

    def get_folder_entity(self, project_name, folder_id):
        self._hierarchy_model.get_folder_entity(project_name, folder_id)

    def get_versions_action_items(self, project_name, version_ids):
        return self._loader_actions_model.get_versions_action_items(
            project_name, version_ids)

    def get_representations_action_items(
            self, project_name, representation_ids):
        return self._loader_actions_model.get_representations_action_items(
            project_name, representation_ids)

    def trigger_action_item(
        self,
        identifier,
        options,
        project_name,
        version_ids,
        representation_ids
    ):
        self._loader_actions_model.trigger_action_item(
            identifier,
            options,
            project_name,
            version_ids,
            representation_ids
        )

    # Selection model wrappers
    def get_selected_project_name(self):
        return self._selection_model.get_selected_project_name()

    def set_selected_project(self, project_name):
        self._selection_model.set_selected_project(project_name)

    # Selection model wrappers
    def get_selected_folder_ids(self):
        return self._selection_model.get_selected_folder_ids()

    def set_selected_folders(self, folder_ids):
        self._selection_model.set_selected_folders(folder_ids)

    def get_selected_version_ids(self):
        return self._selection_model.get_selected_version_ids()

    def set_selected_versions(self, version_ids):
        self._selection_model.set_selected_versions(version_ids)

    def get_selected_representation_ids(self):
        return self._selection_model.get_selected_representation_ids()

    def set_selected_representations(self, repre_ids):
        self._selection_model.set_selected_representations(repre_ids)

    def fill_root_in_source(self, source):
        project_name = self.get_selected_project_name()
        anatomy = self._get_project_anatomy(project_name)
        if anatomy is None:
            return source

        try:
            return anatomy.fill_root(source)
        except Exception:
            return source

    def get_current_context(self):
        if self._host is None:
            return {
                "project_name": None,
                "folder_id": None,
                "task_name": None,
            }
        if hasattr(self._host, "get_current_context"):
            context = self._host.get_current_context()
        else:
            context = get_current_context()
        folder_id = None
        project_name = context.get("project_name")
        asset_name = context.get("asset_name")
        if project_name and asset_name:
            folder = ayon_api.get_folder_by_name(
                project_name, asset_name, fields=["id"]
            )
            if folder:
                folder_id = folder["id"]
        return {
            "project_name": project_name,
            "folder_id": folder_id,
            "task_name": context.get("task_name"),
        }

    def get_loaded_product_ids(self):
        if self._host is None:
            return set()

        context = self.get_current_context()
        project_name = context["project_name"]
        if not project_name:
            return set()

        if not self._loaded_products_cache.is_valid:
            if isinstance(self._host, ILoadHost):
                containers = self._host.get_containers()
            else:
                containers = self._host.ls()
            repre_ids = {c.get("representation") for c in containers}
            repre_ids.discard(None)
            product_ids = self._products_model.get_product_ids_by_repre_ids(
                project_name, repre_ids
            )
            self._loaded_products_cache.update_data(product_ids)
        return self._loaded_products_cache.get_data()

    def is_loaded_products_supported(self):
        return self._host is not None

    def _get_project_anatomy(self, project_name):
        if not project_name:
            return None
        cache = self._project_anatomy_cache[project_name]
        if not cache.is_valid:
            cache.update_data(Anatomy(project_name))
        return cache.get_data()

    def _create_event_system(self):
        return QueuedEventSystem()

    def _emit_event(self, topic, data=None):
        self._event_system.emit(topic, data or {}, "controller")
