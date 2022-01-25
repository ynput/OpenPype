import os
import json
import copy
import collections
import datetime
from abc import ABCMeta, abstractmethod
import six

import openpype.version

from .constants import (
    GLOBAL_SETTINGS_KEY,
    SYSTEM_SETTINGS_KEY,
    PROJECT_SETTINGS_KEY,
    PROJECT_ANATOMY_KEY,
    LOCAL_SETTING_KEY,
    M_OVERRIDEN_KEY
)


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

    # Getters for specific version overrides
    @abstractmethod
    def get_studio_system_settings_overrides_for_version(self, version):
        """Studio system settings overrides for specific version.

        Args:
            version(str): OpenPype version for which settings should be
                returned.

        Returns:
            None: If the version does not have system settings overrides.
            dict: Document with overrides data.
        """
        pass

    @abstractmethod
    def get_studio_project_anatomy_overrides_for_version(self, version):
        """Studio project anatomy overrides for specific version.

        Args:
            version(str): OpenPype version for which settings should be
                returned.

        Returns:
            None: If the version does not have system settings overrides.
            dict: Document with overrides data.
        """
        pass

    @abstractmethod
    def get_studio_project_settings_overrides_for_version(self, version):
        """Studio project settings overrides for specific version.

        Args:
            version(str): OpenPype version for which settings should be
                returned.

        Returns:
            None: If the version does not have system settings overrides.
            dict: Document with overrides data.
        """
        pass

    @abstractmethod
    def get_project_settings_overrides_for_version(
        self, project_name, version
    ):
        """Studio project settings overrides for specific project and version.

        Args:
            project_name(str): Name of project for which the overrides should
                be loaded.
            version(str): OpenPype version for which settings should be
                returned.

        Returns:
            None: If the version does not have system settings overrides.
            dict: Document with overrides data.
        """
        pass

    # Clear methods - per version
    # - clearing may be helpfull when a version settings were created for
    #   testing purposes
    @abstractmethod
    def clear_studio_system_settings_overrides_for_version(self, version):
        """Remove studio system settings overrides for specific version.

        If version is not available then skip processing.
        """
        pass

    @abstractmethod
    def clear_studio_project_settings_overrides_for_version(self, version):
        """Remove studio project settings overrides for specific version.

        If version is not available then skip processing.
        """
        pass

    @abstractmethod
    def clear_studio_project_anatomy_overrides_for_version(self, version):
        """Remove studio project anatomy overrides for specific version.

        If version is not available then skip processing.
        """
        pass

    @abstractmethod
    def clear_project_settings_overrides_for_version(
        self, version, project_name
    ):
        """Remove studio project settings overrides for project and version.

        If version is not available then skip processing.
        """
        pass

    # Get versions that are available for each type of settings
    @abstractmethod
    def get_available_studio_system_settings_overrides_versions(self):
        """OpenPype versions that have any studio system settings overrides.

        Returns:
            list<str>: OpenPype versions strings.
        """
        pass

    @abstractmethod
    def get_available_studio_project_anatomy_overrides_versions(self):
        """OpenPype versions that have any studio project anatomy overrides.

        Returns:
            list<str>: OpenPype versions strings.
        """
        pass

    @abstractmethod
    def get_available_studio_project_settings_overrides_versions(self):
        """OpenPype versions that have any studio project settings overrides.

        Returns:
            list<str>: OpenPype versions strings.
        """
        pass

    @abstractmethod
    def get_available_project_settings_overrides_versions(self, project_name):
        """OpenPype versions that have any project settings overrides.

        Args:
            project_name(str): Name of project.

        Returns:
            list<str>: OpenPype versions strings.
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
    key_suffix = "_versioned"
    _version_order_key = "versions_order"

    def __init__(self):
        # Get mongo connection
        from openpype.lib import OpenPypeMongoConnection
        from avalon.api import AvalonMongoDB

        settings_collection = OpenPypeMongoConnection.get_mongo_client()

        self._anatomy_keys = None
        self._attribute_keys = None

        self._version_order_checked = False

        self._system_settings_key = SYSTEM_SETTINGS_KEY + self.key_suffix
        self._project_settings_key = PROJECT_SETTINGS_KEY + self.key_suffix
        self._project_anatomy_key = PROJECT_ANATOMY_KEY + self.key_suffix
        self._current_version = openpype.version.__version__

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
            # Pop key from overriden metadata
            if (
                M_OVERRIDEN_KEY in general_data
                and key in general_data[M_OVERRIDEN_KEY]
            ):
                general_data[M_OVERRIDEN_KEY].remove(key)
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

        overriden_keys = system_general.get(M_OVERRIDEN_KEY) or []
        for key in self.global_general_keys:
            if key not in globals_data:
                continue

            system_general[key] = globals_data[key]
            if key not in overriden_keys:
                overriden_keys.append(key)

        if overriden_keys:
            system_general[M_OVERRIDEN_KEY] = overriden_keys

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
                "type": self._system_settings_key,
                "version": self._current_version
            },
            {
                "type": self._system_settings_key,
                "data": system_settings_data,
                "version": self._current_version
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
            project_name, self._project_settings_key, data_cache
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
                project_name, self._project_anatomy_key, data_cache
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
            "is_default": is_default,
            "version": self._current_version
        }
        replace_data = {
            "type": doc_type,
            "data": data_cache.data,
            "is_default": is_default,
            "version": self._current_version
        }
        if not is_default:
            replace_filter["project_name"] = project_name
            replace_data["project_name"] = project_name

        self.collection.replace_one(
            replace_filter,
            replace_data,
            upsert=True
        )

    def _check_version_order(self):
        """This method will work only in OpenPype process.

        Will create/update mongo document where OpenPype versions are stored
        in semantic version order.

        This document can be then used to find closes version of settings in
        processes where 'OpenPypeVersion' is not available.
        """
        # Do this step only once
        if self._version_order_checked:
            return
        self._version_order_checked = True

        from openpype.lib.openpype_version import get_OpenPypeVersion

        OpenPypeVersion = get_OpenPypeVersion()
        # Skip if 'OpenPypeVersion' is not available
        if OpenPypeVersion is None:
            return

        # Query document holding sorted list of version strings
        doc = self.collection.find_one({"type": self._version_order_key})
        if not doc:
            # Just create the document if does not exists yet
            self.collection.replace_one(
                {"type": self._version_order_key},
                {
                    "type": self._version_order_key,
                    "versions": [self._current_version]
                },
                upsert=True
            )
            return

        # Skip if current version is already available
        if self._current_version in doc["versions"]:
            return

        # Add all versions into list
        objected_versions = [
            OpenPypeVersion(version=self._current_version)
        ]
        for version_str in doc["versions"]:
            objected_versions.append(OpenPypeVersion(version=version_str))

        # Store version string by their order
        new_versions = []
        for version in sorted(objected_versions):
            new_versions.append(str(version))

        # Update versions list and push changes to Mongo
        doc["versions"] = new_versions
        self.collection.replace_one(
            {"type": self._version_order_key},
            doc,
            upsert=True
        )

    def _find_closest_settings(self, key, legacy_key, additional_filters=None):
        """Try to find closes available versioned settings for settings key.

        This method should be used only if settings for current OpenPype
        version are not available.

        Args:
            key(str): Settings key under which are settings stored ("type").
            legacy_key(str): Settings key under which were stored not versioned
                settings.
            additional_filters(dict): Additional filters of document. Used
                for project specific settings.
        """
        # Trigger check of versions
        self._check_version_order()

        doc_filters = {
            "type": {"$in": [key, legacy_key]}
        }
        if additional_filters:
            doc_filters.update(additional_filters)

        # Query base data of each settings doc
        other_versions = self.collection.find(
            doc_filters,
            {
                "_id": True,
                "version": True,
                "type": True
            }
        )
        # Query doc with list of sorted versions
        versioned_doc = self.collection.find_one(
            {"type": self._version_order_key}
        )
        # Separate queried docs
        legacy_settings_doc = None
        versioned_settings_by_version = {}
        for doc in other_versions:
            if doc["type"] == legacy_key:
                legacy_settings_doc = doc
            elif doc["type"] == key:
                versioned_settings_by_version[doc["version"]] = doc

        # Cases when only legacy settings can be used
        if (
            # There are not versioned documents yet
            not versioned_settings_by_version
            # Versioned document is not available at all
            # - this can happen only if old build of OpenPype was used
            or not versioned_doc
            # Current OpenPype version is not available
            # - something went really wrong when this happens
            or self._current_version not in versioned_doc["versions"]
        ):
            if not legacy_settings_doc:
                return None
            return self.collection.find_one(
                {"_id": legacy_settings_doc["_id"]}
            )

        # Separate versions to lower and higher and keep their order
        lower_versions = []
        higher_versions = []
        before = True
        for version_str in versioned_doc["versions"]:
            if version_str == self._current_version:
                before = False
            elif before:
                lower_versions.append(version_str)
            else:
                higher_versions.append(version_str)

        # Use legacy settings doc as source document
        src_doc_id = None
        if legacy_settings_doc:
            src_doc_id = legacy_settings_doc["_id"]

        # Find highest version which has available settings
        if lower_versions:
            for version_str in reversed(lower_versions):
                doc = versioned_settings_by_version.get(version_str)
                if doc:
                    src_doc_id = doc["_id"]
                    break

        # Use versions with higher version only if there are not legacy
        #   settings and there are not any versions before
        if src_doc_id is None and higher_versions:
            for version_str in higher_versions:
                doc = versioned_settings_by_version.get(version_str)
                if doc:
                    src_doc_id = doc["_id"]
                    break

        if src_doc_id is None:
            return src_doc_id
        return self.collection.find_one({"_id": src_doc_id})

    def _find_closest_system_settings(self):
        return self._find_closest_settings(
            self._system_settings_key,
            SYSTEM_SETTINGS_KEY
        )

    def _find_closest_project_settings(self, project_name):
        if project_name is None:
            additional_filters = {"is_default": True}
        else:
            additional_filters = {"project_name": project_name}

        return self._find_closest_settings(
            self._project_settings_key,
            PROJECT_SETTINGS_KEY,
            additional_filters
        )

    def _find_closest_project_anatomy(self):
        additional_filters = {"is_default": True}
        return self._find_closest_settings(
            self._project_anatomy_key,
            PROJECT_ANATOMY_KEY,
            additional_filters
        )

    def _get_studio_system_settings_overrides_for_version(self, version=None):
        if version is None:
            version = self._current_version

        return self.collection.find_one({
            "type": self._system_settings_key,
            "version": version
        })

    def _get_project_settings_overrides_for_version(
        self, project_name, version=None
    ):
        if version is None:
            version = self._current_version

        document_filter = {
            "type": self._project_settings_key,
            "version": version
        }
        if project_name is None:
            document_filter["is_default"] = True
        else:
            document_filter["project_name"] = project_name
        return self.collection.find_one(document_filter)

    def _get_project_anatomy_overrides_for_version(self, version=None):
        if version is None:
            version = self._current_version

        return self.collection.find_one({
            "type": self._project_settings_key,
            "is_default": True,
            "version": version
        })

    def get_studio_system_settings_overrides(self):
        """Studio overrides of system settings."""
        if self.system_settings_cache.is_outdated:
            globals_document = self.collection.find_one({
                "type": GLOBAL_SETTINGS_KEY
            })
            system_settings_document = (
                self._get_studio_system_settings_overrides_for_version()
            )
            if system_settings_document is None:
                system_settings_document = self._find_closest_system_settings()

            merged_document = self._apply_global_settings(
                system_settings_document, globals_document
            )

            self.system_settings_cache.update_from_document(merged_document)
        return self.system_settings_cache.data_copy()

    def _get_project_settings_overrides(self, project_name):
        if self.project_settings_cache[project_name].is_outdated:
            document = self._get_project_settings_overrides_for_version(
                project_name
            )
            if document is None:
                document = self._find_closest_project_settings(project_name)
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
                document = self._get_project_anatomy_overrides_for_version()
                if document is None:
                    document = self._find_closest_project_anatomy()
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

    # Implementations of abstract methods to get overrides for version
    def get_studio_system_settings_overrides_for_version(self, version):
        return self._get_studio_system_settings_overrides_for_version(version)

    def get_studio_project_anatomy_overrides_for_version(self, version):
        return self._get_project_anatomy_overrides_for_version(version)

    def get_studio_project_settings_overrides_for_version(self, version):
        return self._get_project_settings_overrides_for_version(None, version)

    def get_project_settings_overrides_for_version(
        self, project_name, version
    ):
        return self._get_project_settings_overrides_for_version(
            project_name, version
        )

    # Implementations of abstract methods to clear overrides for version
    def clear_studio_system_settings_overrides_for_version(self, version):
        self.collection.delete_one({
            "type": self._system_settings_key,
            "version": version
        })

    def clear_studio_project_settings_overrides_for_version(self, version):
        self.collection.delete_one({
            "type": self._project_settings_key,
            "version": version,
            "is_default": True
        })

    def clear_studio_project_anatomy_overrides_for_version(self, version):
        self.collection.delete_one({
            "type": self._project_anatomy_key,
            "version": version
        })

    def clear_project_settings_overrides_for_version(
        self, version, project_name
    ):
        self.collection.delete_one({
            "type": self._project_settings_key,
            "version": version,
            "project_name": project_name
        })

    # Get available versions for settings type
    def get_available_studio_system_settings_overrides_versions(self):
        docs = self.collection.find(
            {"type": self._system_settings_key},
            {"version": True}
        )
        return {doc["version"] for doc in docs}

    def get_available_studio_project_anatomy_overrides_versions(self):
        docs = self.collection.find(
            {"type": self._project_anatomy_key},
            {"version": True}
        )
        return {doc["version"] for doc in docs}

    def get_available_studio_project_settings_overrides_versions(self):
        docs = self.collection.find(
            {"type": self._project_settings_key, "is_default": True},
            {"version": True}
        )
        return {doc["version"] for doc in docs}

    def get_available_project_settings_overrides_versions(self, project_name):
        docs = self.collection.find(
            {"type": self._project_settings_key, "project_name": project_name},
            {"version": True}
        )
        return {doc["version"] for doc in docs}


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
