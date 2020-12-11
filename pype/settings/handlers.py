import os
import json
import logging
from abc import ABCMeta, abstractmethod
import six
import pype
from .constants import (
    M_OVERRIDEN_KEY,
    M_ENVIRONMENT_KEY,
    M_DYNAMIC_KEY_LABEL,
    M_POP_KEY,

    METADATA_KEYS,

    SYSTEM_SETTINGS_KEY,
    ENVIRONMENTS_KEY,
    PROJECT_SETTINGS_KEY,
    PROJECT_ANATOMY_KEY
)

JSON_EXC = getattr(json.decoder, "JSONDecodeError", ValueError)


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


class SettingsFileHandler(SettingsHandler):
    def __init__(self):
        self.log = logging.getLogger("SettingsFileHandler")

        # Folder where studio overrides are stored
        studio_overrides_dir = os.getenv("PYPE_PROJECT_CONFIGS")
        if not studio_overrides_dir:
            studio_overrides_dir = os.path.dirname(os.path.dirname(
                os.path.abspath(pype.__file__)
            ))
        system_settings_path = os.path.join(
            studio_overrides_dir, SYSTEM_SETTINGS_KEY + ".json"
        )

        # File where studio's default project overrides are stored
        project_settings_filename = PROJECT_SETTINGS_KEY + ".json"
        project_settings_path = os.path.join(
            studio_overrides_dir, project_settings_filename
        )

        project_anatomy_filename = PROJECT_ANATOMY_KEY + ".json"
        project_anatomy_path = os.path.join(
            studio_overrides_dir, project_anatomy_filename
        )

        self.studio_overrides_dir = studio_overrides_dir
        self.system_settings_path = system_settings_path

        self.project_settings_filename = project_settings_filename
        self.project_anatomy_filename = project_anatomy_filename

        self.project_settings_path = project_settings_path
        self.project_anatomy_path = project_anatomy_path

    def load_json_file(self, fpath):
        # Load json data
        try:
            with open(fpath, "r") as opened_file:
                return json.load(opened_file)

        except JSON_EXC:
            self.log.warning(
                "File has invalid json format \"{}\"".format(fpath),
                exc_info=True
            )
        return {}

    def path_to_project_settings(self, project_name):
        if not project_name:
            return self.project_settings_path
        return os.path.join(
            self.studio_overrides_dir,
            project_name,
            self.project_settings_filename
        )

    def path_to_project_anatomy(self, project_name):
        if not project_name:
            return self.project_anatomy_path
        return os.path.join(
            self.studio_overrides_dir,
            project_name,
            self.project_anatomy_filename
        )

    def save_studio_settings(self, data):
        """Save studio overrides of system settings.

        Do not use to store whole system settings data with defaults but only
        it's overrides with metadata defining how overrides should be applied
        in load function. For loading should be used function
        `studio_system_settings`.

        Args:
            data(dict): Data of studio overrides with override metadata.
        """
        dirpath = os.path.dirname(self.system_settings_path)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        self.log.debug(
            "Saving studio overrides. Output path: {}".format(
                self.system_settings_path
            )
        )
        with open(self.system_settings_path, "w") as file_stream:
            json.dump(data, file_stream, indent=4)

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
        project_overrides_json_path = self.path_to_project_settings(
            project_name
        )
        dirpath = os.path.dirname(project_overrides_json_path)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        self.log.debug(
            "Saving overrides of project \"{}\". Output path: {}".format(
                project_name, project_overrides_json_path
            )
        )
        with open(project_overrides_json_path, "w") as file_stream:
            json.dump(overrides, file_stream, indent=4)

    def save_project_anatomy(self, project_name, anatomy_data):
        """Save studio overrides of project anatomy data.

        Args:
            project_name(str, null): Project name for which overrides are
                or None for global settings.
            data(dict): Data of project overrides with override metadata.
        """
        project_anatomy_json_path = self.path_to_project_anatomy(project_name)
        dirpath = os.path.dirname(project_anatomy_json_path)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        self.log.debug(
            "Saving anatomy of project \"{}\". Output path: {}".format(
                project_name, project_anatomy_json_path
            )
        )
        with open(project_anatomy_json_path, "w") as file_stream:
            json.dump(anatomy_data, file_stream, indent=4)

    def get_studio_system_settings_overrides(self):
        """Studio overrides of system settings."""
        if os.path.exists(self.system_settings_path):
            return self.load_json_file(self.system_settings_path)
        return {}

    def get_studio_project_settings_overrides(self):
        """Studio overrides of default project settings."""
        if os.path.exists(self.project_settings_path):
            return self.load_json_file(self.project_settings_path)
        return {}

    def get_studio_project_anatomy_overrides(self):
        """Studio overrides of default project anatomy data."""
        if os.path.exists(self.project_anatomy_path):
            return self.load_json_file(self.project_anatomy_path)
        return {}

    def get_project_settings_overrides(self, project_name):
        """Studio overrides of project settings for specific project.

        Args:
            project_name(str): Name of project for which data should be loaded.

        Returns:
            dict: Only overrides for entered project, may be empty dictionary.
        """
        path_to_json = self.path_to_project_settings(project_name)
        if not os.path.exists(path_to_json):
            return {}
        return self.load_json_file(path_to_json)

    def get_project_anatomy_overrides(self, project_name):
        """Studio overrides of project anatomy for specific project.

        Args:
            project_name(str): Name of project for which data should be loaded.

        Returns:
            dict: Only overrides for entered project, may be empty dictionary.
        """
        if not project_name:
            return {}

        path_to_json = self.path_to_project_anatomy(project_name)
        if not os.path.exists(path_to_json):
            return {}
        return self.load_json_file(path_to_json)
