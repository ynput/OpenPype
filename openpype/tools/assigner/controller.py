from openpype.lib.events import EventSystem
from openpype.pipeline import legacy_io
from .model import AssignerToolModel


class AssignerController(object):
    def __init__(self, host):
        self._host = host

        # Create tool event system
        self._event_system = EventSystem()

        # Create main tool model
        self._model = AssignerToolModel(self)

    @property
    def host(self):
        """Quick access to related host."""

        return self._host

    @property
    def event_system(self):
        return self._event_system

    @property
    def project_name(self):
        """Current context project name."""

        return legacy_io.active_project()

    def get_container_groups(self):
        return self._model.get_container_groups()

    def get_current_containers_subset_items(self):
        return self._model.get_current_containers_subset_items()

    def get_thumbnail_for_version(self, version_id):
        return self._model.get_thumbnail_for_version(version_id)

    def get_context_thumbnail_sources(self):
        return self._model.get_context_thumbnail_sources()
