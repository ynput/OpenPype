from abc import abstractmethod
from openpype.modules import OpenPypeInterface


class ISettingsChangeListener(OpenPypeInterface):
    """Module has plugin paths to return.

    Expected result is dictionary with keys "publish", "create", "load" or
    "actions" and values as list or string.
    {
        "publish": ["path/to/publish_plugins"]
    }
    """
    @abstractmethod
    def on_system_settings_save(
        self, old_value, new_value, changes, new_value_metadata
    ):
        pass

    @abstractmethod
    def on_project_settings_save(
        self, old_value, new_value, changes, project_name, new_value_metadata
    ):
        pass

    @abstractmethod
    def on_project_anatomy_save(
        self, old_value, new_value, changes, project_name, new_value_metadata
    ):
        pass
