from uuid import uuid4
from pype.api import Logger


class PypeModule:
    """Base class of pype module."""
    enabled = False
    name = None
    _id = None

    def __init__(self, settings):
        if self.name is None:
            self.name = self.__class__.__name__

        self.log = Logger().get_logger(self.name)

        self.settings = settings.get(self.name)
        self.enabled = settings.get("enabled", False)
        self._id = uuid4()

    @property
    def id(self):
        return self._id

    def startup_environments(self):
        return {}
