import logging

from openpype.lib.events import QueuedEventSystem

from openpype.tools.ayon_utils.models import ProjectsModel, HierarchyModel

from .abstract import AbstractController
from .models import SelectionModel, ProductsModel


class LoaderController(AbstractController):
    def __init__(self):
        self._log = None
        self._event_system = self._create_event_system()

        self._selection_model = SelectionModel(self)
        self._projects_model = ProjectsModel(self)
        self._hierarchy_model = HierarchyModel(self)
        self._products_model = ProductsModel(self)

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

    def get_product_type_items(self, project_name):
        return self._products_model.get_product_type_items(project_name)

    def get_folder_entity(self, project_name, folder_id):
        self._hierarchy_model.get_folder_entity(project_name, folder_id)

    # Selection model wrappers
    def get_selected_project_name(self):
        return self._selection_model.get_selected_project_name()

    def set_selected_project(self, project_name):
        self._selection_model.set_selected_project(project_name)

    # Selection model wrappers
    def get_selected_folder_ids(self):
        self._selection_model.get_selected_folder_ids()

    def set_selected_folders(self, folder_ids):
        self._selection_model.set_selected_folders(folder_ids)

    def _create_event_system(self):
        return QueuedEventSystem()

    def _emit_event(self, topic, data=None):
        self._event_system.emit(topic, data or {}, "controller")
