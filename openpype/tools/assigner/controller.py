import os
from openpype.lib.events import EventSystem
from openpype.pipeline import legacy_io
from .model import AssignerToolModel


class AssignerController(object):
    def __init__(self, host):
        self._default_thumbnail_content = None

        self._host = host

        # Create tool event system and register controller's callbacks
        self._event_system = EventSystem()
        self._register_callbacks()

        # Create main tool model
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

    @property
    def default_thumbnail_content(self):
        if self._default_thumbnail_content is None:
            filepath = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "images",
                "default_thumbnail.png"
            )
            with open(filepath, "rb") as stream:
                content = stream.read()
            self._default_thumbnail_content = content
        return self._default_thumbnail_content

    def container_selection_changed(self, event):
        self._model.set_current_containers(event["container_ids"])

    def get_container_groups(self):
        return self._model.get_container_groups()

    def get_current_containers_subset_items(self):
        return self._model.get_current_containers_subset_items()

    def get_thumbnail_sources(self):
        return [self.default_thumbnail_content]
