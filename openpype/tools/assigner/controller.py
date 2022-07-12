from openpype.pipeline import legacy_io
from .model import AssignerToolModel


class AssignerController(object):
    def __init__(self, host):
        self._host = host
        self._model = AssignerToolModel(self)

    @property
    def host(self):
        """Quick access to related host."""

        return self._host

    @property
    def project_name(self):
        """Current context project name."""

        return legacy_io.active_project()

    def get_container_groups(self):
        return self._model.get_container_groups()
