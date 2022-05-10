import os
import json
import copy
import collections

from abc import abstractmethod

from .base_entity import BaseItemEntity
from .lib import (
    NOT_SET,
    WRAPPER_TYPES,
    SCHEMA_KEY_SYSTEM_SETTINGS,
    SCHEMA_KEY_PROJECT_SETTINGS,
    OverrideState,
    SchemasHub,
    DynamicSchemaValueCollector
)
from .exceptions import (
    SchemaError,
    InvalidKeySymbols
)
from openpype.settings.constants import (
    SYSTEM_SETTINGS_KEY,
    PROJECT_SETTINGS_KEY,
    PROJECT_ANATOMY_KEY,
    KEY_REGEX
)
from openpype.settings.exceptions import SaveWarningExc

from openpype.settings.lib import (
    DEFAULTS_DIR,

    get_default_settings,
    reset_default_settings,

    get_studio_system_settings_overrides,
    get_studio_system_settings_overrides_for_version,
    save_studio_settings,
    get_available_studio_system_settings_overrides_versions,

    get_studio_project_settings_overrides,
    get_studio_project_settings_overrides_for_version,
    get_studio_project_anatomy_overrides,
    get_studio_project_anatomy_overrides_for_version,
    get_project_settings_overrides,
    get_project_settings_overrides_for_version,
    get_project_anatomy_overrides,
    save_project_settings,
    save_project_anatomy,

    get_available_project_settings_overrides_versions,
    get_available_studio_project_settings_overrides_versions,
    get_available_studio_project_anatomy_overrides_versions,

    apply_overrides
)


class RootEntity(BaseItemEntity):
    """Abstract class for root entities.

    Root entity is top hierarchy entity without parent. Should care about
    saving and must have access to all entities in it's scope.
    """
    schema_types = ["root"]

    def __init__(self, schema_hub, reset, main_schema_name=None):
        self.schema_hub = schema_hub
        if not main_schema_name:
            main_schema_name = "schema_main"
        schema_data = schema_hub.get_schema(main_schema_name)

        super(RootEntity, self).__init__(schema_data)
        self._require_restart_callbacks = []
        self._item_ids_require_restart = set()
        self._item_initialization()
        if reset:
            self.reset()

    @property
    def override_state(self):
        """Current OverrideState."""
        return self._override_state

    @property
    def require_restart(self):
        return bool(self._item_ids_require_restart)

    def add_require_restart_change_callback(self, callback):
        self._require_restart_callbacks.append(callback)

    def _on_require_restart_change(self):
        for callback in self._require_restart_callbacks:
            callback()

    def add_item_require_restart(self, item):
        was_empty = len(self._item_ids_require_restart) == 0
        self._item_ids_require_restart.add(item.id)
        if was_empty:
            self._on_require_restart_change()

    def remove_item_require_restart(self, item):
        if item.id not in self._item_ids_require_restart:
            return

        self._item_ids_require_restart.remove(item.id)
        if not self._item_ids_require_restart:
            self._on_require_restart_change()

    @abstractmethod
    def reset(self):
        """Reset values and entities to initial state.

        Reload settings and entities should reset their changes or be
        recreated.
        """
        pass

    def __getitem__(self, key):
        return self.non_gui_children[key]

    def __setitem__(self, key, value):
        self.non_gui_children[key].set(value)

    def __iter__(self):
        for key in self.keys():
            yield key

    def get(self, key, default=None):
        return self.non_gui_children.get(key, default)

    def set(self, value):
        """Set value."""
        new_value = self.convert_to_valid_type(value)
        for _key, _value in new_value.items():
            self.non_gui_children[_key].set(_value)

    def has_child_with_key(self, key):
        return key in self.non_gui_children

    def keys(self):
        return self.non_gui_children.keys()

    def values(self):
        return self.non_gui_children.values()

    def items(self):
        return self.non_gui_children.items()

    def _add_children(self, schema_data, first=True):
        added_children = []
        children_deque = collections.deque()
        for _children_schema in schema_data["children"]:
            children_schemas = self.schema_hub.resolve_schema_data(
                _children_schema
            )
            for children_schema in children_schemas:
                children_deque.append(children_schema)

        while children_deque:
            children_schema = children_deque.popleft()

            if children_schema["type"] in WRAPPER_TYPES:
                _children_schema = copy.deepcopy(children_schema)
                wrapper_children = self._add_children(
                    children_schema["children"], False
                )
                _children_schema["children"] = wrapper_children
                added_children.append(_children_schema)
                continue

            child_obj = self.create_schema_object(children_schema, self)
            self.children.append(child_obj)
            added_children.append(child_obj)
            if isinstance(child_obj, self.schema_hub.gui_types):
                continue

            if child_obj.key in self.non_gui_children:
                raise KeyError(
                    "Duplicated key \"{}\"".format(child_obj.key)
                )
            self.non_gui_children[child_obj.key] = child_obj

        if not first:
            return added_children

        for child_obj in added_children:
            self.gui_layout.append(child_obj)

    def _item_initialization(self):
        # Store `self` to `root_item` for children entities
        self.root_item = self

        # Children are stored by key as keys are immutable and are defined by
        # schema
        self.valid_value_types = (dict, )

        self.children = []
        self.non_gui_children = {}
        self.gui_layout = []

        self._add_children(self.schema_data)

        self.schema_validations()

    def schema_validations(self):
        for child_entity in self.children:
            if child_entity.is_group:
                reason = (
                    "Root entity \"{}\" has child with `is_group`"
                    " attribute set to True but root can't save overrides."
                ).format(self.__class__.__name__)
                raise SchemaError(reason)
            child_entity.schema_validations()

        for key in self.non_gui_children.keys():
            if not KEY_REGEX.match(key):
                raise InvalidKeySymbols(self.path, key)

    @abstractmethod
    def get_entity_from_path(self, path):
        """Return entity matching passed path."""
        pass

    def create_schema_object(self, schema_data, *args, **kwargs):
        """Create entity by entered schema data.

        Available entities are loaded on first run. Children entities can call
        this method.
        """
        return self.schema_hub.create_schema_object(
            schema_data, *args, **kwargs
        )

    def set_override_state(self, state, ignore_missing_defaults=None):
        """Set override state and trigger it on children.

        Method will discard all changes in hierarchy and use values, metadata
        and all kind of values for defined state.

        Args:
            state (OverrideState): State to which should be data changed.
        """
        if not ignore_missing_defaults:
            ignore_missing_defaults = False

        self._override_state = state
        for child_obj in self.non_gui_children.values():
            child_obj.set_override_state(state, ignore_missing_defaults)

    def on_change(self):
        """Trigger callbacks on change."""
        for callback in self.on_change_callbacks:
            callback()

    def on_child_change(self, _child_entity):
        """Whan any children has changed."""
        self.on_change()

    def collect_static_entities_by_path(self):
        output = {}
        for child_obj in self.non_gui_children.values():
            result = child_obj.collect_static_entities_by_path()
            if result:
                output.update(result)
        return output

    def get_child_path(self, child_entity):
        """Return path of children entity"""
        for key, _child_entity in self.non_gui_children.items():
            if _child_entity is child_entity:
                return key
        raise ValueError("Didn't found child {}".format(child_entity))

    @property
    def value(self):
        """Value for current override state without metadata."""
        output = {}
        for key, child_obj in self.non_gui_children.items():
            output[key] = child_obj.value
        return output

    def collect_dynamic_schema_entities(self):
        output = DynamicSchemaValueCollector(self.schema_hub)
        if self._override_state is not OverrideState.DEFAULTS:
            return output

        for child_obj in self.non_gui_children.values():
            child_obj.collect_dynamic_schema_entities(output)

        return output

    def settings_value(self):
        """Value for current override state with metadata.

        This is what should be stored on save method.
        """
        if self._override_state is OverrideState.NOT_DEFINED:
            return NOT_SET

        if self._override_state is not OverrideState.DEFAULTS:
            output = {}
            for key, child_obj in self.non_gui_children.items():
                if child_obj.is_dynamic_schema_node:
                    continue
                value = child_obj.settings_value()
                if value is not NOT_SET:
                    output[key] = value
            return output

        output = {}
        for key, child_obj in self.non_gui_children.items():
            child_value = child_obj.settings_value()
            if not child_obj.is_file and not child_obj.file_item:
                for _key, _value in child_value.items():
                    new_key = "/".join([key, _key])
                    output[new_key] = _value
            else:
                output[key] = child_value
        return output

    @property
    def has_studio_override(self):
        """Any children has studio override.

        Return's relevant data only if override state is STUDIO or PROJECT.

        Returns:
            bool: True if any children has studio overrides.
        """
        if self._override_state >= OverrideState.STUDIO:
            for child_obj in self.non_gui_children.values():
                if child_obj.has_studio_override:
                    return True
        return False

    @property
    def has_project_override(self):
        """Any children has project override.

        Return's relevant data only if override state is PROJECT.

        Returns:
            bool: True if any children has project overrides.
        """
        if self._override_state >= OverrideState.PROJECT:
            for child_obj in self.non_gui_children.values():
                if child_obj.has_project_override:
                    return True
        return False

    @property
    def has_unsaved_changes(self):
        """Entity contain unsaved changes.

        Root on it's own can't have any modifications so looks only on
        children.

        Returns:
            bool: True if has unsaved changes.
        """
        for child_obj in self.non_gui_children.values():
            if child_obj.has_unsaved_changes:
                return True
        return False

    def _discard_changes(self, on_change_trigger):
        """Implementation of abstract method only trigger children callback."""
        for child_obj in self.non_gui_children.values():
            child_obj.discard_changes(on_change_trigger)

    def _add_to_studio_default(self, *args, **kwargs):
        """Implementation of abstract method only trigger children callback."""
        for child_obj in self.non_gui_children.values():
            child_obj.add_to_studio_default(*args, **kwargs)

    def _remove_from_studio_default(self, on_change_trigger):
        """Implementation of abstract method only trigger children callback."""
        for child_obj in self.non_gui_children.values():
            child_obj.remove_from_studio_default(on_change_trigger)

    def _add_to_project_override(self, *args, **kwargs):
        """Implementation of abstract method only trigger children callback."""
        for child_obj in self.non_gui_children.values():
            child_obj.add_to_project_override(*args, **kwargs)

    def _remove_from_project_override(self, on_change_trigger):
        """Implementation of abstract method only trigger children callback."""
        for child_obj in self.non_gui_children.values():
            child_obj.remove_from_project_override(on_change_trigger)

    def save(self):
        """Save values for current override state.

        Values are stored with current values and modifications.
        """
        if self._override_state is OverrideState.NOT_DEFINED:
            raise ValueError(
                "Can't save if override state is set to NOT_DEFINED"
            )

        if self._override_state is OverrideState.DEFAULTS:
            self._save_default_values()
            reset_default_settings()

        elif self._override_state is OverrideState.STUDIO:
            self._save_studio_values()

        elif self._override_state is OverrideState.PROJECT:
            self._save_project_values()

        # Trigger reset to reload entities
        self.reset()

    @abstractmethod
    def defaults_dir(self):
        """Abstract method to return directory path to defaults.

        Implementation of `_save_default_values` requires defaults dir where
        default data will be stored.
        """
        pass

    def _save_default_values(self):
        """Save default values.

        Do not call this method, always use `save`. Manually called method
        won't save current values as defaults if override state is not set to
        DEFAULTS.
        """
        settings_value = self.settings_value()

        defaults_dir = self.defaults_dir()
        for file_path, value in settings_value.items():
            subpath = file_path + ".json"

            output_path = os.path.join(defaults_dir, subpath)
            dirpath = os.path.dirname(output_path)
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)

            self.log.debug("Saving data to: {}\n{}".format(subpath, value))
            with open(output_path, "w") as file_stream:
                json.dump(value, file_stream, indent=4)

        dynamic_values_item = self.collect_dynamic_schema_entities()
        dynamic_values_item.save_values()

    @abstractmethod
    def _save_studio_values(self):
        """Save studio override values."""
        pass

    @abstractmethod
    def _save_project_values(self):
        """Save project override values."""
        pass

    def is_in_defaults_state(self):
        """Api callback to check if current state is DEFAULTS."""
        return self._override_state is OverrideState.DEFAULTS

    def is_in_studio_state(self):
        """Api callback to check if current state is STUDIO."""
        return self._override_state is OverrideState.STUDIO

    def is_in_project_state(self):
        """Api callback to check if current state is PROJECT."""
        return self._override_state is OverrideState.PROJECT

    def set_defaults_state(self):
        """Change override state to DEFAULTS."""
        self.set_override_state(OverrideState.DEFAULTS)

    def set_studio_state(self):
        """Change override state to STUDIO."""
        self.set_override_state(OverrideState.STUDIO)

    def set_project_state(self):
        """Change override state to PROJECT."""
        self.set_override_state(OverrideState.PROJECT)


class SystemSettings(RootEntity):
    """Root entity for system settings.

    Allows to modify system settings via entity system and loaded schemas.

    Args:
        set_studio_state (bool): Set studio values on initialization. By
            default is set to True.
        reset (bool): Reset values on initialization. By default is set to
            True.
        schema_data (dict): Pass schema data to entity. This is for development
            and debugging purposes.
    """
    root_key = SYSTEM_SETTINGS_KEY

    def __init__(
        self,
        set_studio_state=True,
        reset=True,
        schema_hub=None,
        source_version=None
    ):
        if schema_hub is None:
            # Load system schemas
            schema_hub = SchemasHub(SCHEMA_KEY_SYSTEM_SETTINGS)

        self._source_version = source_version

        super(SystemSettings, self).__init__(schema_hub, reset)

        if set_studio_state:
            self.set_studio_state()

    @property
    def source_version(self):
        return self._source_version

    def get_entity_from_path(self, path):
        """Return system settings entity."""
        path_parts = path.split("/")
        first_part = path_parts[0]
        output = self
        if first_part == self.root_key:
            path_parts.pop(0)

        for path_part in path_parts:
            output = output[path_part]
        return output

    def _reset_values(self):
        default_value = get_default_settings()[SYSTEM_SETTINGS_KEY]
        for key, child_obj in self.non_gui_children.items():
            value = default_value.get(key, NOT_SET)
            child_obj.update_default_value(value)

        if self._source_version is None:
            studio_overrides, version = get_studio_system_settings_overrides(
                return_version=True
            )
            self._source_version = version

        else:
            studio_overrides = (
                get_studio_system_settings_overrides_for_version(
                    self._source_version
                )
            )

        for key, child_obj in self.non_gui_children.items():
            value = studio_overrides.get(key, NOT_SET)
            child_obj.update_studio_value(value)

    def reset(self, new_state=None, source_version=None):
        """Discard changes and reset entit's values.

        Reload default values and studio override values and update entities.

        Args:
            new_state (OverrideState): It is possible to change override state
                during reset. Current state is used if not defined.
        """
        if new_state is None:
            new_state = self._override_state

        if new_state is OverrideState.NOT_DEFINED:
            new_state = OverrideState.DEFAULTS

        if new_state is OverrideState.PROJECT:
            raise ValueError("System settings can't store poject overrides.")

        if source_version is not None:
            self._source_version = source_version

        self._reset_values()
        self.set_override_state(new_state)

    def get_available_source_versions(self, sorted=None):
        if self.is_in_studio_state():
            return self.get_available_studio_versions(sorted=sorted)
        return []

    def get_available_studio_versions(self, sorted=None):
        return get_available_studio_system_settings_overrides_versions(
            sorted=sorted
        )

    def defaults_dir(self):
        """Path to defaults directory.

        Implementation of abstract method.
        """
        return os.path.join(DEFAULTS_DIR, SYSTEM_SETTINGS_KEY)

    def _save_studio_values(self):
        settings_value = self.settings_value()

        self.log.debug("Saving system settings: {}".format(
            json.dumps(settings_value, indent=4)
        ))
        save_studio_settings(settings_value)
        # Reset source version after restart
        self._source_version = None

    def _save_project_values(self):
        """System settings can't have project overrides.

        Raises:
            ValueError: Raise when called as entity can't use or store project
                overrides.
        """
        raise ValueError("System settings can't save project overrides.")


class ProjectSettings(RootEntity):
    """Root entity for project settings.

    Allows to modify project settings via entity system and loaded schemas.

    Args:
        project_name (str): Project name which overrides will be loaded.
            Use `None` to modify studio defaults.
        change_state (bool): Set values on initialization. By
            default is set to True.
        reset (bool): Reset values on initialization. By default is set to
            True.
        schema_data (dict): Pass schema data to entity. This is for development
            and debugging purposes.
    """
    root_key = PROJECT_SETTINGS_KEY

    def __init__(
        self,
        project_name=None,
        change_state=True,
        reset=True,
        schema_hub=None,
        source_version=None,
        anatomy_source_version=None
    ):
        self._project_name = project_name

        self._system_settings_entity = None
        self._source_version = source_version
        self._anatomy_source_version = anatomy_source_version

        if schema_hub is None:
            # Load system schemas
            schema_hub = SchemasHub(SCHEMA_KEY_PROJECT_SETTINGS)

        super(ProjectSettings, self).__init__(schema_hub, reset)

        if change_state:
            if self.project_name is None:
                self.set_studio_state()
            else:
                self.set_project_state()

    @property
    def source_version(self):
        return self._source_version

    @property
    def anatomy_source_version(self):
        return self._anatomy_source_version

    @property
    def project_name(self):
        return self._project_name

    @project_name.setter
    def project_name(self, project_name):
        self.change_project(project_name)

    @property
    def system_settings_entity(self):
        output = self._system_settings_entity
        if output is None:
            output = SystemSettings(set_studio_state=False)
            self._system_settings_entity = output

        if self.override_state is OverrideState.DEFAULTS:
            if output.override_state is not OverrideState.DEFAULTS:
                output.set_defaults_state()
        elif self.override_state > OverrideState.DEFAULTS:
            if output.override_state <= OverrideState.DEFAULTS:
                try:
                    output.set_studio_state()
                except Exception:
                    output.set_defaults_state()
        return output

    def get_entity_from_path(self, path):
        path_parts = path.split("/")
        first_part = path_parts[0]
        # TODO replace with constants
        if first_part == "system_settings":
            output = self.system_settings_entity
            path_parts.pop(0)
        else:
            output = self
            if first_part == "project_settings":
                path_parts.pop(0)

        for path_part in path_parts:
            output = output[path_part]
        return output

    def change_project(self, project_name, source_version=None):
        if project_name == self._project_name:
            if (
                source_version is None
                or source_version == self._source_version
            ):
                if not self.is_in_project_state():
                    self.set_project_state()
                return

        self._source_version = source_version
        self._anatomy_source_version = None

        self._set_values_for_project(project_name)
        self.set_project_state()

    def _reset_values(self):
        default_values = {
            PROJECT_SETTINGS_KEY: get_default_settings()[PROJECT_SETTINGS_KEY],
            PROJECT_ANATOMY_KEY: get_default_settings()[PROJECT_ANATOMY_KEY]
        }
        for key, child_obj in self.non_gui_children.items():
            value = default_values.get(key, NOT_SET)
            child_obj.update_default_value(value)

        self._set_values_for_project(self.project_name)

    def _set_values_for_project(self, project_name):
        self._project_name = project_name
        if project_name:
            project_settings_overrides = (
                get_studio_project_settings_overrides()
            )
            project_anatomy_overrides = (
                get_studio_project_anatomy_overrides()
            )
        else:
            if self._source_version is None:
                project_settings_overrides, version = (
                    get_studio_project_settings_overrides(return_version=True)
                )
                self._source_version = version
            else:
                project_settings_overrides = (
                    get_studio_project_settings_overrides_for_version(
                        self._source_version
                    )
                )

            if self._anatomy_source_version is None:
                project_anatomy_overrides, anatomy_version = (
                    get_studio_project_anatomy_overrides(return_version=True)
                )
                self._anatomy_source_version = anatomy_version
            else:
                project_anatomy_overrides = (
                    get_studio_project_anatomy_overrides_for_version(
                        self._anatomy_source_version
                    )
                )

        studio_overrides = {
            PROJECT_SETTINGS_KEY: project_settings_overrides,
            PROJECT_ANATOMY_KEY: project_anatomy_overrides
        }

        for key, child_obj in self.non_gui_children.items():
            value = studio_overrides.get(key, NOT_SET)
            child_obj.update_studio_value(value)

        if not project_name:
            return

        if self._source_version is None:
            project_settings_overrides, version = (
                get_project_settings_overrides(
                    project_name, return_version=True
                )
            )
            self._source_version = version
        else:
            project_settings_overrides = (
                get_project_settings_overrides_for_version(
                    project_name, self._source_version
                )
            )

        project_override_value = {
            PROJECT_SETTINGS_KEY: project_settings_overrides,
            PROJECT_ANATOMY_KEY: get_project_anatomy_overrides(project_name)
        }
        for key, child_obj in self.non_gui_children.items():
            value = project_override_value.get(key, NOT_SET)
            child_obj.update_project_value(value)

    def get_available_source_versions(self, sorted=None):
        if self.is_in_studio_state():
            return self.get_available_studio_versions(sorted=sorted)
        elif self.is_in_project_state():
            return get_available_project_settings_overrides_versions(
                self.project_name, sorted=sorted
            )
        return []

    def get_available_studio_versions(self, sorted=None):
        return get_available_studio_project_settings_overrides_versions(
            sorted=sorted
        )

    def get_available_anatomy_source_versions(self, sorted=None):
        if self.is_in_studio_state():
            return get_available_studio_project_anatomy_overrides_versions(
                sorted=sorted
            )
        return []

    def reset(self, new_state=None):
        """Discard changes and reset entit's values.

        Reload default values and studio override values and update entities.

        Args:
            new_state (OverrideState): It is possible to change override state
                during reset. Current state is used if not defined.
        """
        if new_state is None:
            new_state = self._override_state

        if new_state is OverrideState.NOT_DEFINED:
            new_state = OverrideState.DEFAULTS

        self._system_settings_entity = None

        self._reset_values()
        self.set_override_state(new_state)

    def defaults_dir(self):
        """Path to defaults directory.

        Implementation of abstract method.
        """
        return DEFAULTS_DIR

    def _save_studio_values(self):
        settings_value = self.settings_value()

        self._validate_values_to_save(settings_value)

        self._source_version = None
        self._anatomy_source_version = None

        self.log.debug("Saving project settings: {}".format(
            json.dumps(settings_value, indent=4)
        ))
        project_settings = settings_value.get(PROJECT_SETTINGS_KEY) or {}
        project_anatomy = settings_value.get(PROJECT_ANATOMY_KEY) or {}

        warnings = []
        try:
            save_project_settings(self.project_name, project_settings)
        except SaveWarningExc as exc:
            warnings.extend(exc.warnings)

        try:
            save_project_anatomy(self.project_name, project_anatomy)
        except SaveWarningExc as exc:
            warnings.extend(exc.warnings)

        if warnings:
            raise SaveWarningExc(warnings)

    def _validate_values_to_save(self, value):
        pass

    def _save_project_values(self):
        """Project overrides are saved same ways as studio overrides."""
        self._save_studio_values()
