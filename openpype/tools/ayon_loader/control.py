import logging

from openpype.lib.events import QueuedEventSystem
from openpype.pipeline import Anatomy
from openpype.tools.ayon_utils.models import (
    ProjectsModel,
    HierarchyModel,
    NestedCacheItem,
)

from .abstract import AbstractController
from .models import SelectionModel, ProductsModel, LoaderActionsModel


class LoaderController(AbstractController):
    def __init__(self):
        self._log = None
        self._event_system = self._create_event_system()

        self._project_anatomy_cache = NestedCacheItem(levels=1)
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
        self._products_model.reset()
        self._hierarchy_model.reset()
        self._projects_model.refresh()
        self._emit_event("controller.reset.finished")

    def get_current_project(self):
        return None

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
        product_ids,
        representation_ids
    ):
        self._loader_actions_model.trigger_action_item(
            identifier,
            options,
            project_name,
            product_ids,
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
