from openpype.api import (
    Logger
)

log = Logger.get_logger(__name__)


class OpenPypePyblishPluginMixin:
    executable_in_thread = False

    state_message = None
    state_percent = None
    _state_change_callbacks = []

    @classmethod
    def get_attribute_defs(cls):
        """Publish attribute definitions.

        Attributes available for all families in plugin's `families` attribute.
        Returns:
            list<AbtractAttrDef>: Attribute definitions for plugin.
        """
        return []

    def set_state(self, percent=None, message=None):
        """Inner callback of plugin that would help to show in UI state.

        Plugin have registered callbacks on state change which could trigger
        update message and percent in UI and repaint the change.

        This part must be optional and should not be used to display errors
        or for logging.

        Message should be short without details.

        Args:
            percent(int): Percent of processing in range <1-100>.
            message(str): Message which will be shown to user (if in UI).
        """
        if percent is not None:
            self.state_percent = percent

        if message:
            self.state_message = message

        for callback in self._state_change_callbacks:
            callback(self)
