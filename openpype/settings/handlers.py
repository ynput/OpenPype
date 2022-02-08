import os
import json
import copy
import logging
import collections
import datetime
from abc import ABCMeta, abstractmethod
import six
import openpype
from .constants import (
    GLOBAL_SETTINGS_KEY,
    SYSTEM_SETTINGS_KEY,
    PROJECT_SETTINGS_KEY,
    PROJECT_ANATOMY_KEY,
    LOCAL_SETTING_KEY,
    M_OVERRIDDEN_KEY
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
        data = {}
        if document:
            if "data" in document:
                data = document["data"]
            elif "value" in document:
                value = document["value"]
                if value:
                    data = json.loads(value)
        self.data = data

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
    global_general_keys = (
        "openpype_path",
        "admin_password",
        "disk_mapping",
        "production_version",
        "staging_version"
    )

    def __init__(self):
        # Get mongo connection
        from openpype.lib import OpenPypeMongoConnection
        from avalon.api import AvalonMongoDB

        settings_collection = OpenPypeMongoConnection.get_mongo_client()

        self._anatomy_keys = None
        self._attribute_keys = None
        # TODO prepare version of pype
        # - pype version should define how are settings saved and loaded

        database_name = os.environ["OPENPYPE_DATABASE_NAME"]
        # TODO modify to not use hardcoded keys
        collection_name = "settings"

        self.settings_collection = settings_collection

        self.database_name = database_name
        self.collection_name = collection_name

        self.collection = settings_collection[database_name][collection_name]
        self.avalon_db = AvalonMongoDB()

        self.system_settings_cache = CacheValues()
        self.project_settings_cache = collections.defaultdict(CacheValues)
        self.project_anatomy_cache = collections.defaultdict(CacheValues)

    def _prepare_project_settings_keys(self):
        from .entities import ProjectSettings
        # Prepare anatomy keys and attribute keys
        # NOTE this is cached on first import
        # - keys may change only on schema change which should not happen
        #   during production
        project_settings_root = ProjectSettings(
            reset=False, change_state=False
        )
        anatomy_entity = project_settings_root["project_anatomy"]
        anatomy_keys = set(anatomy_entity.keys())
        anatomy_keys.remove("attributes")
        attribute_keys = set(anatomy_entity["attributes"].keys())

        self._anatomy_keys = anatomy_keys
        self._attribute_keys = attribute_keys

    @property
    def anatomy_keys(self):
        if self._anatomy_keys is None:
            self._prepare_project_settings_keys()
        return self._anatomy_keys

    @property
    def attribute_keys(self):
        if self._attribute_keys is None:
            self._prepare_project_settings_keys()
        return self._attribute_keys

    def _extract_global_settings(self, data):
        """Extract global settings data from system settings overrides.

        This is now limited to "general" key in system settings which must be
        set as group in schemas.

        Returns:
            dict: Global settings extracted from system settings data.
        """
        output = {}
        if "general" not in data:
            return output

        general_data = data["general"]

        # Add predefined keys to global settings if are set
        for key in self.global_general_keys:
            if key not in general_data:
                continue
            # Pop key from values
            output[key] = general_data.pop(key)
            # Pop key from overridden metadata
            if (
                M_OVERRIDDEN_KEY in general_data
                and key in general_data[M_OVERRIDDEN_KEY]
            ):
                general_data[M_OVERRIDDEN_KEY].remove(key)
        return output

    def _apply_global_settings(
        self, system_settings_document, globals_document
    ):
        """Apply global settings data to system settings.

        Applification is skipped if document with global settings is not
        available or does not have set data in.

        System settings document is "faked" like it exists if global document
        has set values.

        Args:
            system_settings_document (dict): System settings document from
                MongoDB.
            globals_document (dict): Global settings document from MongoDB.

        Returns:
            Merged document which has applied global settings data.
        """
        # Skip if globals document is not available
        if (
            not globals_document
            or "data" not in globals_document
            or not globals_document["data"]
        ):
            return system_settings_document

        globals_data = globals_document["data"]
        # Check if data contain any key from predefined keys
        any_key_found = False
        if globals_data:
            for key in self.global_general_keys:
                if key in globals_data:
                    any_key_found = True
                    break

        # Skip if any key from predefined key was not found in globals
        if not any_key_found:
            return system_settings_document

        # "Fake" system settings document if document does not exist
        # - global settings document may exist but system settings not yet
        if not system_settings_document:
            system_settings_document = {}

        if "data" in system_settings_document:
            system_settings_data = system_settings_document["data"]
        else:
            system_settings_data = {}
            system_settings_document["data"] = system_settings_data

        if "general" in system_settings_data:
            system_general = system_settings_data["general"]
        else:
            system_general = {}
            system_settings_data["general"] = system_general

        overridden_keys = system_general.get(M_OVERRIDDEN_KEY) or []
        for key in self.global_general_keys:
            if key not in globals_data:
                continue

            system_general[key] = globals_data[key]
            if key not in overridden_keys:
                overridden_keys.append(key)

        if overridden_keys:
            system_general[M_OVERRIDDEN_KEY] = overridden_keys

        return system_settings_document

    def save_studio_settings(self, data):
        """Save studio overrides of system settings.

        Do not use to store whole system settings data with defaults but only
        it's overrides with metadata defining how overrides should be applied
        in load function. For loading should be used function
        `studio_system_settings`.

        Args:
            data(dict): Data of studio overrides with override metadata.
        """
        # Update cache
        self.system_settings_cache.update_data(data)

        # Get copy of just updated cache
        system_settings_data = self.system_settings_cache.data_copy()

        # Extract global settings from system settings
        global_settings = self._extract_global_settings(
            system_settings_data
        )

        # Store system settings
        self.collection.replace_one(
            {
                "type": SYSTEM_SETTINGS_KEY
            },
            {
                "type": SYSTEM_SETTINGS_KEY,
                "data": system_settings_data
            },
            upsert=True
        )

        # Store global settings
        self.collection.replace_one(
            {
                "type": GLOBAL_SETTINGS_KEY
            },
            {
                "type": GLOBAL_SETTINGS_KEY,
                "data": global_settings
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

        if project_name is not None:
            self._save_project_anatomy_data(project_name, data_cache)

        else:
            self._save_project_data(
                project_name, PROJECT_ANATOMY_KEY, data_cache
            )

    @classmethod
    def prepare_mongo_update_dict(cls, in_data):
        data = {}
        for key, value in in_data.items():
            if not isinstance(value, dict):
                data[key] = value
                continue

            new_value = cls.prepare_mongo_update_dict(value)
            for _key, _value in new_value.items():
                new_key = ".".join((key, _key))
                data[new_key] = _value

        return data

    def _save_project_anatomy_data(self, project_name, data_cache):
        # Create copy of data as they will be modified during save
        new_data = data_cache.data_copy()

        # Prepare avalon project document
        collection = self.avalon_db.database[project_name]
        project_doc = collection.find_one({
            "type": "project"
        })
        if not project_doc:
            raise ValueError((
                "Project document of project \"{}\" does not exists."
                " Create project first."
            ).format(project_name))

        # Project's data
        update_dict_data = {}
        project_doc_data = project_doc.get("data") or {}
        attributes = new_data.pop("attributes")
        _applications = attributes.pop("applications", None) or []
        for key, value in attributes.items():
            if (
                key in project_doc_data
                and project_doc_data[key] == value
            ):
                continue
            update_dict_data[key] = value

        update_dict_config = {}

        applications = []
        for application in _applications:
            if not application:
                continue
            if isinstance(application, six.string_types):
                applications.append({"name": application})

        new_data["apps"] = applications

        for key, value in new_data.items():
            project_doc_value = project_doc.get(key)
            if key in project_doc and project_doc_value == value:
                continue
            update_dict_config[key] = value

        if not update_dict_data and not update_dict_config:
            return

        data_changes = self.prepare_mongo_update_dict(update_dict_data)

        # Update dictionary of changes that will be changed in mongo
        update_dict = {}
        for key, value in data_changes.items():
            new_key = "data.{}".format(key)
            update_dict[new_key] = value

        for key, value in update_dict_config.items():
            new_key = "config.{}".format(key)
            update_dict[new_key] = value

        collection.update_one(
            {"type": "project"},
            {"$set": update_dict}
        )

    def _save_project_data(self, project_name, doc_type, data_cache):
        is_default = bool(project_name is None)
        replace_filter = {
            "type": doc_type,
            "is_default": is_default
        }
        replace_data = {
            "type": doc_type,
            "data": data_cache.data,
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
            system_settings_document = None
            globals_document = None
            docs = self.collection.find({
                # Use `$or` as system settings may have more filters in future
                "$or": [
                    {"type": GLOBAL_SETTINGS_KEY},
                    {"type": SYSTEM_SETTINGS_KEY},
                ]
            })
            for doc in docs:
                doc_type = doc["type"]
                if doc_type == GLOBAL_SETTINGS_KEY:
                    globals_document = doc
                elif doc_type == SYSTEM_SETTINGS_KEY:
                    system_settings_document = doc

            merged_document = self._apply_global_settings(
                system_settings_document, globals_document
            )

            self.system_settings_cache.update_from_document(merged_document)
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

    def project_doc_to_anatomy_data(self, project_doc):
        """Convert project document to anatomy data.

        Probably should fill missing keys and values.
        """
        if not project_doc:
            return {}

        attributes = {}
        project_doc_data = project_doc.get("data") or {}
        for key in self.attribute_keys:
            value = project_doc_data.get(key)
            if value is not None:
                attributes[key] = value

        project_doc_config = project_doc.get("config") or {}

        app_names = set()
        if not project_doc_config or "apps" not in project_doc_config:
            set_applications = False
        else:
            set_applications = True
            for app_item in project_doc_config["apps"]:
                if not app_item:
                    continue
                app_name = app_item.get("name")
                if app_name:
                    app_names.add(app_name)

        if set_applications:
            attributes["applications"] = list(app_names)

        output = {"attributes": attributes}
        for key in self.anatomy_keys:
            value = project_doc_config.get(key)
            if value is not None:
                output[key] = value

        return output

    def _get_project_anatomy_overrides(self, project_name):
        if self.project_anatomy_cache[project_name].is_outdated:
            if project_name is None:
                document_filter = {
                    "type": PROJECT_ANATOMY_KEY,
                    "is_default": True
                }
                document = self.collection.find_one(document_filter)
                self.project_anatomy_cache[project_name].update_from_document(
                    document
                )
            else:
                collection = self.avalon_db.database[project_name]
                project_doc = collection.find_one({"type": "project"})
                self.project_anatomy_cache[project_name].update_data(
                    self.project_doc_to_anatomy_data(project_doc)
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
        from openpype.lib import (
            OpenPypeMongoConnection,
            get_local_site_id
        )

        if local_site_id is None:
            local_site_id = get_local_site_id()
        settings_collection = OpenPypeMongoConnection.get_mongo_client()

        # TODO prepare version of pype
        # - pype version should define how are settings saved and loaded

        database_name = os.environ["OPENPYPE_DATABASE_NAME"]
        # TODO modify to not use hardcoded keys
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
                "data": self.local_settings_cache.data
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
