from openpype.api import (
    Logger
)

import pyblish.api

log = Logger.get_logger(__name__)


class OpenPypePyblishPluginMixin:
    executable_in_thread = False

    state_message = None
    state_percent = None
    _state_change_callbacks = []

    @classmethod
    def get_family_attribute_defs(cls, family):
        return None

    def set_state(self, percent=None, message=None):
        if percent is not None:
            self.state_percent = percent

        if message:
            self.state_message = message

        for callback in self._state_change_callbacks:
            callback(self)
