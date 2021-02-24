import os
import json
import copy
import logging
import collections
import datetime
from abc import ABCMeta, abstractmethod
import six
import pype
from .constants import (
    SYSTEM_SETTINGS_KEY,
    PROJECT_SETTINGS_KEY,
    PROJECT_ANATOMY_KEY,
    LOCAL_SETTING_KEY
)
from .lib import load_json_file

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


@six.add_metaclass(ABCMeta)
class LocalSettingsHandler:
    """Handler that should handle about storing and loading of local settings.

    Local settings are "workstation" specific modifications that modify how
    system and project settings look on the workstation and only there.
    """
    @abstractmethod
    def save_local_settings(self, data):
        """Save local data of local settings.

        Args:
            data(dict): Data of local data with override metadata.
        """
        pass

    @abstractmethod
    def get_local_settings(self):
        """Studio overrides of system settings."""
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
            return load_json_file(self.system_settings_path)
        return {}

    def get_studio_project_settings_overrides(self):
        """Studio overrides of default project settings."""
        if os.path.exists(self.project_settings_path):
            return load_json_file(self.project_settings_path)
        return {}

    def get_studio_project_anatomy_overrides(self):
        """Studio overrides of default project anatomy data."""
        if os.path.exists(self.project_anatomy_path):
            return load_json_file(self.project_anatomy_path)
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
        return load_json_file(path_to_json)

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
        return load_json_file(path_to_json)


class CacheValues:
    cache_lifetime = 10

    def __init__(self):
        self.data = None
        self.creation_time = None

    def data_copy(self):
        if not self.data:
            return {}
        return copy.deepcopy(self.data)

    def update_data(self, data):
        self.data = data
        self.creation_time = datetime.datetime.now()

    def update_from_document(self, document):
        value = "{}"
        if document:
            value = document.get("value") or value
        self.data = json.loads(value)

    def to_json_string(self):
        return json.dumps(self.data or {})

    @property
    def is_outdated(self):
        if self.creation_time is None:
            return True
        delta = (datetime.datetime.now() - self.creation_time).seconds
        return delta > self.cache_lifetime


class MongoSettingsHandler(SettingsHandler):
    """Settings handler that use mongo for storing and loading of settings."""

    def __init__(self):
        # Get mongo connection
        from pype.lib import PypeMongoConnection
        settings_collection = PypeMongoConnection.get_mongo_client()

        # TODO prepare version of pype
        # - pype version should define how are settings saved and loaded

        # TODO modify to not use hardcoded keys
        database_name = "pype"
        collection_name = "settings"

        self.settings_collection = settings_collection

        self.database_name = database_name
        self.collection_name = collection_name

        self.collection = settings_collection[database_name][collection_name]

        self.system_settings_cache = CacheValues()
        self.project_settings_cache = collections.defaultdict(CacheValues)
        self.project_anatomy_cache = collections.defaultdict(CacheValues)

    def save_studio_settings(self, data):
        """Save studio overrides of system settings.

        Do not use to store whole system settings data with defaults but only
        it's overrides with metadata defining how overrides should be applied
        in load function. For loading should be used function
        `studio_system_settings`.

        Args:
            data(dict): Data of studio overrides with override metadata.
        """
        self.system_settings_cache.update_data(data)

        self.collection.replace_one(
            {
                "type": SYSTEM_SETTINGS_KEY
            },
            {
                "type": SYSTEM_SETTINGS_KEY,
                "value": self.system_settings_cache.to_json_string()
            },
            upsert=True
        )

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
        data_cache = self.project_settings_cache[project_name]
        data_cache.update_data(overrides)

        self._save_project_data(
            project_name, PROJECT_SETTINGS_KEY, data_cache
        )

    def save_project_anatomy(self, project_name, anatomy_data):
        """Save studio overrides of project anatomy data.

        Args:
            project_name(str, null): Project name for which overrides are
                or None for global settings.
            data(dict): Data of project overrides with override metadata.
        """
        data_cache = self.project_anatomy_cache[project_name]
        data_cache.update_data(anatomy_data)

        self._save_project_data(
            project_name, PROJECT_ANATOMY_KEY, data_cache
        )

    def _save_project_data(self, project_name, doc_type, data_cache):
        is_default = bool(project_name is None)
        replace_filter = {
            "type": doc_type,
            "is_default": is_default
        }
        replace_data = {
            "type": doc_type,
            "value": data_cache.to_json_string(),
            "is_default": is_default
        }
        if not is_default:
            replace_filter["project_name"] = project_name
            replace_data["project_name"] = project_name

        self.collection.replace_one(
            replace_filter,
            replace_data,
            upsert=True
        )

    def get_studio_system_settings_overrides(self):
        """Studio overrides of system settings."""
        if self.system_settings_cache.is_outdated:
            document = self.collection.find_one({
                "type": SYSTEM_SETTINGS_KEY
            })

            self.system_settings_cache.update_from_document(document)
        return self.system_settings_cache.data_copy()

    def _get_project_settings_overrides(self, project_name):
        if self.project_settings_cache[project_name].is_outdated:
            document_filter = {
                "type": PROJECT_SETTINGS_KEY,
            }
            if project_name is None:
                document_filter["is_default"] = True
            else:
                document_filter["project_name"] = project_name
            document = self.collection.find_one(document_filter)
            self.project_settings_cache[project_name].update_from_document(
                document
            )
        return self.project_settings_cache[project_name].data_copy()

    def get_studio_project_settings_overrides(self):
        """Studio overrides of default project settings."""
        return self._get_project_settings_overrides(None)

    def get_project_settings_overrides(self, project_name):
        """Studio overrides of project settings for specific project.

        Args:
            project_name(str): Name of project for which data should be loaded.

        Returns:
            dict: Only overrides for entered project, may be empty dictionary.
        """
        if not project_name:
            return {}
        return self._get_project_settings_overrides(project_name)

    def _get_project_anatomy_overrides(self, project_name):
        if self.project_anatomy_cache[project_name].is_outdated:
            document_filter = {
                "type": PROJECT_ANATOMY_KEY,
            }
            if project_name is None:
                document_filter["is_default"] = True
            else:
                document_filter["project_name"] = project_name
            document = self.collection.find_one(document_filter)
            self.project_anatomy_cache[project_name].update_from_document(
                document
            )
        return self.project_anatomy_cache[project_name].data_copy()

    def get_studio_project_anatomy_overrides(self):
        """Studio overrides of default project anatomy data."""
        return self._get_project_anatomy_overrides(None)

    def get_project_anatomy_overrides(self, project_name):
        """Studio overrides of project anatomy for specific project.

        Args:
            project_name(str): Name of project for which data should be loaded.

        Returns:
            dict: Only overrides for entered project, may be empty dictionary.
        """
        if not project_name:
            return {}
        return self._get_project_anatomy_overrides(project_name)


class MongoLocalSettingsHandler(LocalSettingsHandler):
    """Settings handler that use mongo for store and load local settings.

    Data have 2 query criteria. First is key "type" stored in constant
    `LOCAL_SETTING_KEY`. Second is key "site_id" which value can be obstained
    with `get_local_site_id` function.
    """

    def __init__(self, local_site_id=None):
        # Get mongo connection
        from pype.lib import (
            PypeMongoConnection,
            get_local_site_id
        )

        if local_site_id is None:
            local_site_id = get_local_site_id()
        settings_collection = PypeMongoConnection.get_mongo_client()

        # TODO prepare version of pype
        # - pype version should define how are settings saved and loaded

        # TODO modify to not use hardcoded keys
        database_name = "pype"
        collection_name = "settings"

        self.settings_collection = settings_collection

        self.database_name = database_name
        self.collection_name = collection_name

        self.collection = settings_collection[database_name][collection_name]

        self.local_site_id = local_site_id

        self.local_settings_cache = CacheValues()

    def save_local_settings(self, data):
        """Save local settings.

        Args:
            data(dict): Data of studio overrides with override metadata.
        """
        data = data or {}

        self.local_settings_cache.update_data(data)

        self.collection.replace_one(
            {
                "type": LOCAL_SETTING_KEY,
                "site_id": self.local_site_id
            },
            {
                "type": LOCAL_SETTING_KEY,
                "site_id": self.local_site_id,
                "value": self.local_settings_cache.to_json_string()
            },
            upsert=True
        )

    def get_local_settings(self):
        """Local settings for local site id."""
        if self.local_settings_cache.is_outdated:
            document = self.collection.find_one({
                "type": LOCAL_SETTING_KEY,
                "site_id": self.local_site_id
            })

            self.local_settings_cache.update_from_document(document)

        return self.local_settings_cache.data_copy()
