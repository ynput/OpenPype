from openpype.lib.events import EventSystem
from openpype.pipeline import legacy_io
from .model import AssignerToolModel


class AssignerController(object):
    def __init__(self, host):
        self._host = host

        self._event_system = EventSystem()
        self._register_callbacks()

        self._model = AssignerToolModel(self)

    def _register_callbacks(self):
        self._event_system.add_callback(
            "container.selection.changed", self.container_selection_changed
        )

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
