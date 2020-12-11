from abc import ABCMeta, abstractmethod
import six


@six.add_metaclass(ABCMeta)
class SettingsHandler:
    @abstractmethod
    def save_studio_settings(self, data):
        """Save studio overrides of system settings.

        Do not use to store whole system settings data with defaults but only
        it's overrides with metadata defining how overrides should be applied
        in load function. For loading should be used function
        `studio_system_settings`.

        Args:
            data(dict): Data of studio overrides with override metadata.
        """
        pass

    @abstractmethod
    def save_project_settings(self, project_name, overrides):
        """Save studio overrides of project settings.

        Data are saved for specific project or as defaults for all projects.

        Do not use to store whole project settings data with defaults but only
        it's overrides with metadata defining how overrides should be applied
        in load function. For loading should be used function
        `get_studio_project_settings_overrides` for global project settings
        and `get_project_settings_overrides` for project specific settings.

        Args:
            project_name(str, null): Project name for which overrides are
                or None for global settings.
            data(dict): Data of project overrides with override metadata.
        """
        pass

    @abstractmethod
    def save_project_anatomy(self, project_name, anatomy_data):
        """Save studio overrides of project anatomy data.

        Args:
            project_name(str, null): Project name for which overrides are
                or None for global settings.
            data(dict): Data of project overrides with override metadata.
        """
        pass

    @abstractmethod
    def get_studio_system_settings_overrides(self):
        """Studio overrides of system settings."""
        pass

    @abstractmethod
    def get_studio_project_settings_overrides(self):
        """Studio overrides of default project settings."""
        pass

    @abstractmethod
    def get_studio_project_anatomy_overrides(self):
        """Studio overrides of default project anatomy data."""
        pass

    @abstractmethod
    def get_project_settings_overrides(self, project_name):
        """Studio overrides of project settings for specific project.

        Args:
            project_name(str): Name of project for which data should be loaded.

        Returns:
            dict: Only overrides for entered project, may be empty dictionary.
        """
        pass

    @abstractmethod
    def get_project_anatomy_overrides(self, project_name):
        """Studio overrides of project anatomy for specific project.

        Args:
            project_name(str): Name of project for which data should be loaded.

        Returns:
            dict: Only overrides for entered project, may be empty dictionary.
        """
        pass

