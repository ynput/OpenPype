import os
import json
import copy
import inspect
import logging
from abc import ABCMeta, abstractmethod, abstractproperty

import six

from .lib import (
    NOT_SET,
    gui_schema
)
from .constants import (
    SYSTEM_SETTINGS_KEY,
    WRAPPER_TYPES,
    OverrideState
)
from pype.settings.lib import (
    DEFAULTS_DIR,

    get_default_settings,

    get_studio_system_settings_overrides,

    save_studio_settings,

    find_environments,
    DuplicatedEnvGroups
)

# from pype.api import Logger
class Logger:
    def get_logger(self, name):
        return logging.getLogger(name)


class InvalidValueType(Exception):
    msg_template = "{}"

    def __init__(self, valid_types, invalid_type, key):
        msg = ""
        if key:
            msg += "Key \"{}\". ".format(key)

        joined_types = ", ".join(
            [str(valid_type) for valid_type in valid_types]
        )
        msg += "Got invalid type \"{}\". Expected: {}".format(
            invalid_type, joined_types
        )
        self.msg = msg
        super(InvalidValueType, self).__init__(msg)


@six.add_metaclass(ABCMeta)
class BaseEntity:
    """Partially abstract class for Setting's item type workflow."""
    # `is_input_type` attribute says if has implemented item type methods
    is_input_type = True
    # Each input must have implemented default value for development
    # when defaults are not filled yet.
    default_input_value = NOT_SET
    # Will allow to show actions for the item type (disabled for proxies) else
    # item is skipped and try to trigger actions on it's parent.
    allow_actions = True
    # If item can store environment values
    allow_to_environment = False
    # Item will expand to full width in grid layout
    expand_in_grid = False

    def __init__(self, schema_data, parent, is_dynamic_item=False):
        self.schema_data = schema_data
        self.parent = parent

        # Log object
        self._log = None

        # Item path attribute (may be filled or be dynamic)
        self._path = None

        # These should be set on initialization and not change then
        self.valid_value_types = getattr(self, "valid_value_types", NOT_SET)
        self.value_on_not_set = getattr(self, "value_on_not_set", NOT_SET)

        self.is_group = False
        self.is_file = False
        self.group_item = None
        self.file_item = None
        self.root_item = None

        # NOTE was `as_widget`
        self.is_dynamic_item = is_dynamic_item
        self.is_in_dynamic_item = False

        self.env_group_key = None
        self.is_env_group = False

        self.roles = None

        # Item require key to be able load or store data
        self.require_key = True

        self.key = None
        self.label = None

        # These attributes may change values during existence of an object
        # Values
        self.default_value = NOT_SET
        self.studio_override_value = NOT_SET
        self.project_override_value = NOT_SET

        # Only for develop mode
        self.defaults_not_set = False

        # Default input attributes
        self.has_default_value = False

        self._has_studio_override = False
        self.had_studio_override = False

        self._has_project_override = False
        self.had_project_override = False

        self.value_is_modified = False

        self.override_state = OverrideState.NOT_DEFINED

        self.on_change_callbacks = []

    @property
    def has_studio_override(self):
        if self.override_state >= OverrideState.STUDIO:
            return self._has_studio_override
        return False

    @property
    def has_project_override(self):
        if self.override_state >= OverrideState.PROJECT:
            return self._has_project_override
        return False

    @property
    def path(self):
        if self._path is not None:
            return self._path

        path = self.parent.get_child_path(self)
        if not self.is_in_dynamic_item and not self.is_dynamic_item:
            self._path = path
        return path

    @abstractmethod
    def get_child_path(self, child_obj):
        pass

    @abstractmethod
    def schema_validations(self):
        pass

    @abstractmethod
    def set_override_state(self, state):
        pass

    @abstractmethod
    def on_value_change(self):
        pass

    @abstractmethod
    def on_change(self):
        pass

    @abstractmethod
    def on_child_change(self, child_obj):
        pass

    @abstractmethod
    def set_value(self, value):
        pass

    def validate_value(self, value):
        if not self.valid_value_types:
            return

        for valid_type in self.valid_value_types:
            if type(value) is valid_type:
                return

        key = getattr(self, "key", None)
        raise InvalidValueType(self.valid_value_types, type(value), key)

    def merge_metadata(self, current_metadata, new_metadata):
        for key, value in new_metadata.items():
            if key not in current_metadata:
                current_metadata[key] = value

            elif key == "groups":
                current_metadata[key].extend(value)

            elif key == "environments":
                for group_key, subvalue in value.items():
                    if group_key not in current_metadata[key]:
                        current_metadata[key][group_key] = []
                    current_metadata[key][group_key].extend(subvalue)

            else:
                raise KeyError("Unknown metadata key: \"{}\"".format(key))
        return current_metadata

    def available_for_role(self, role_name=None):
        if not self.roles:
            return True
        if role_name is None:
            role_name = self.user_role
        return role_name in self.roles

    @property
    def user_role(self):
        """Tool is running with any user role.

        Returns:
            str: user role as string.

        """
        return self.parent.user_role

    @property
    def is_overidable(self):
        """ care about overrides."""
        return self.parent.is_overidable

    @property
    def log(self):
        """Auto created logger for debugging."""
        if self._log is None:
            self._log = Logger().get_logger(self.__class__.__name__)
        return self._log

    @abstractproperty
    def value(self):
        pass

    @abstractmethod
    def update_default_value(self, parent_values):
        """Fill default values on startup or on refresh.

        Default values stored in `pype` repository should update all items in
        schema. Each item should take values for his key and set it's value or
        pass values down to children items.

        Args:
            parent_values (dict): Values of parent's item. But in case item is
                used as widget, `parent_values` contain value for item.
        """
        pass

    @abstractmethod
    def update_studio_values(self, parent_values):
        """Fill studio override values on startup or on refresh.

        Set studio value if is not set to NOT_SET, in that case studio
        overrides are not set yet.

        Args:
            parent_values (dict): Values of parent's item. But in case item is
                used as widget, `parent_values` contain value for item.
        """
        pass

    @abstractmethod
    def update_project_values(self, parent_values):
        """Fill project override values on startup, refresh or project change.

        Set project value if is not set to NOT_SET, in that case project
        overrides are not set yet.

        Args:
            parent_values (dict): Values of parent's item. But in case item is
                used as widget, `parent_values` contain value for item.
        """
        pass

    @abstractproperty
    def schema_types(self):
        pass

    @abstractproperty
    def has_unsaved_changes(self):
        pass

    @abstractproperty
    def child_is_modified(self):
        """Any children item is modified."""
        pass

    @abstractproperty
    def child_has_studio_override(self):
        """Any children item has studio overrides."""
        pass

    @abstractproperty
    def child_has_project_override(self):
        """Any children item has project overrides."""
        pass

    @abstractmethod
    def settings_value(self):
        """Value of an item without key."""
        pass

    def discard_changes(self, on_change_trigger=None):
        initialized = False
        if on_change_trigger is None:
            initialized = True
            on_change_trigger = []

        self._discard_changes(on_change_trigger)

        if initialized:
            for callback in on_change_trigger:
                callback()

    @abstractmethod
    def _discard_changes(self, on_change_trigger):
        """Item's implementation to discard all changes made by user.

        Reset all values to same values as had when opened GUI
        or when changed project.

        Must not affect `had_studio_override` value or `was_overriden`
        value. It must be marked that there are keys/values which are not in
        defaults or overrides.
        """
        pass

    @abstractmethod
    def set_studio_default(self):
        """Item's implementation to set current values as studio's overrides.

        Mark item and it's children as they have studio overrides.
        """
        pass

    @abstractmethod
    def reset_to_pype_default(self):
        """Item's implementation to remove studio overrides.

        Mark item as it does not have studio overrides unset studio
        override values.
        """
        pass

    @abstractmethod
    def remove_overrides(self):
        """Item's implementation to remove project overrides.

        Mark item as does not have project overrides. Must not change
        `was_overriden` attribute value.
        """
        pass

    @abstractmethod
    def set_as_overriden(self):
        """Item's implementation to set values as overriden for project.

        Mark item and all it's children as they're overriden. Must skip
        items with children items that has attributes `is_group`
        and `any_parent_is_group` set to False. In that case those items
        are not meant to be overridable and should trigger the method on it's
        children.

        """
        pass

    @abstractmethod
    def save(self):
        """Save data for current state."""
        pass


class RootEntity(BaseEntity):
    schema_types = ["root"]

    # Root does not have to implement these
    # TODO move them from BaseEntity to ItemEntity
    update_default_value = None
    update_studio_values = None
    update_project_values = None
    schema_validations = None

    def __init__(self, schema_data):
        super(RootEntity, self).__init__(schema_data, None, None)
        self.root_item = self
        self.item_initalization()
        self.reset()

    @abstractmethod
    def reset(self):
        pass

    def __getitem__(self, key):
        return self.non_gui_children[key]

    def __setitem__(self, key, value):
        self.non_gui_children[key].set_value(value)

    def __iter__(self):
        for key in self.keys():
            yield key

    def get(self, key, default=None):
        return self.non_gui_children.get(key, default)

    def keys(self):
        return self.non_gui_children.keys()

    def values(self):
        return self.non_gui_children.values()

    def items(self):
        return self.non_gui_children.items()

    def _add_children(self, schema_data, first=True):
        added_children = []
        for children_schema in schema_data["children"]:
            if children_schema["type"] in WRAPPER_TYPES:
                _children_schema = copy.deepcopy(children_schema)
                wrapper_children = self._add_children(
                    children_schema["children"]
                )
                _children_schema["children"] = wrapper_children
                added_children.append(_children_schema)
                continue

            child_obj = self.create_schema_object(children_schema, self)
            self.children.append(child_obj)
            added_children.append(child_obj)
            if type(child_obj) in self._gui_types:
                continue

            if child_obj.key in self.non_gui_children:
                raise KeyError("Duplicated key \"{}\"".format(child_obj.key))
            self.non_gui_children[child_obj.key] = child_obj

        if not first:
            return added_children

        for child_obj in added_children:
            if isinstance(child_obj, BaseEntity):
                continue
            self.gui_wrappers.append(child_obj)

    def item_initalization(self):
        self._loaded_types = None
        self._gui_types = None
        # Children are stored by key as keys are immutable and are defined by
        # schema
        self.valid_value_types = (dict, )
        self.children = []
        self.non_gui_children = {}
        self.gui_wrappers = []
        self._add_children(self.schema_data)
        for children in self.children:
            children.schema_validations()

    def create_schema_object(self, schema_data, *args, **kwargs):
        if self._loaded_types is None:
            from pype.settings import entities

            known_abstract_classes = (
                BaseEntity,
                entities.ItemEntity,
                entities.InputEntity
            )

            self._loaded_types = {}
            self._gui_types = []
            for attr in dir(entities):
                item = getattr(entities, attr)
                if not inspect.isclass(item):
                    continue

                if not issubclass(item, BaseEntity):
                    continue

                if inspect.isabstract(item):
                    if item in known_abstract_classes:
                        continue
                    item()

                for schema_type in item.schema_types:
                    self._loaded_types[schema_type] = item

                gui_type = getattr(item, "gui_type", False)
                if gui_type:
                    self._gui_types.append(item)

        klass = self._loaded_types.get(schema_data["type"])
        if not klass:
            raise KeyError("Unknown type \"{}\"".format(schema_data["type"]))
        return klass(schema_data, *args, **kwargs)

    def set_override_state(self, state):
        self.override_state = state
        for child_obj in self.non_gui_children.values():
            child_obj.set_override_state(state)

    def set_value(self, value):
        raise KeyError("{} does not allow to use `set_value`.".format(
            self.__class__.__name__
        ))

    def on_value_change(self):
        raise TypeError("{} does not support `on_value_change`".format(
            self.__class__.__name__
        ))

    def on_change(self):
        for callback in self.on_change_callbacks:
            callback()

    def on_child_change(self, child_obj):
        self.on_change()

    def get_child_path(self, child_obj):
        for key, _child_obj in self.non_gui_children.items():
            if _child_obj is child_obj:
                return key
        raise ValueError("Didn't found child {}".format(child_obj))

    @property
    def value(self):
        output = {}
        for key, child_obj in self.non_gui_children.items():
            output[key] = child_obj.value
        return output

    def settings_value(self):
        if self.override_state is OverrideState.NOT_DEFINED:
            return NOT_SET

        output = {}
        for key, child_obj in self.non_gui_children.items():
            value = child_obj.settings_value()
            if self.override_state is OverrideState.DEFAULTS:
                if value is not NOT_SET:
                    raise TypeError((
                        "Child returned NOT_SET on defaults settings. {}"
                    ).format(child_obj.path))

                for _key, _value in value.items():
                    new_key = "/".join([key, _key])
                    output[new_key] = _value

            else:
                if value is not NOT_SET:
                    output[key] = value
        return output

    @property
    def child_has_studio_override(self):
        if self.override_state >= OverrideState.STUDIO:
            for child_obj in self.non_gui_children.values():
                if child_obj.child_has_studio_override:
                    return True
        return False

    @property
    def child_has_project_override(self):
        if self.override_state >= OverrideState.PROJECT:
            for child_obj in self.non_gui_children.values():
                if child_obj.child_has_project_override:
                    return True
        return False

    @property
    def has_unsaved_changes(self):
        for child_obj in self.non_gui_children.values():
            if child_obj.has_unsaved_changes:
                return True
        return False

    @property
    def child_is_modified(self):
        pass

    def _discard_changes(self, on_change_trigger):
        for child_obj in self.non_gui_children.values():
            child_obj.discard_changes(on_change_trigger)

    def remove_overrides(self):
        for child_obj in self.non_gui_children.values():
            child_obj.remove_overrides()

    def reset_to_pype_default(self):
        for child_obj in self.non_gui_children.values():
            child_obj.reset_to_pype_default()

    def set_as_overriden(self):
        for child_obj in self.non_gui_children.values():
            child_obj.set_as_overriden()

    def set_studio_default(self):
        for child_obj in self.non_gui_children.values():
            child_obj.set_studio_default()

    def save(self):
        if self.override_state is OverrideState.NOT_DEFINED:
            raise ValueError(
                "Can't save if override state is set to NOT_DEFINED"
            )

        if not self.items_are_valid():
            return

        if self.override_state is OverrideState.DEFAULTS:
            self.save_default_values()

        elif self.override_state is OverrideState.STUDIO:
            self.save_studio_values()

        elif self.override_state is OverrideState.PROJECT:
            self.save_project_values()

    @abstractmethod
    def items_are_valid(self):
        pass

    @abstractmethod
    def defaults_dir(self):
        pass

    @abstractmethod
    def validate_defaults_to_save(self, value):
        pass

    def save_default_values(self):
        settings_value = self.settings_value()
        if not self.validate_defaults_to_save(settings_value):
            return

        defaults_dir = self.defaults_dir()
        for file_path, value in settings_value.items():
            subpath = file_path + ".json"

            output_path = os.path.join(defaults_dir, subpath)
            dirpath = os.path.dirname(output_path)
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)

            print("Saving data to: ", subpath)
            with open(output_path, "w") as file_stream:
                json.dump(value, file_stream, indent=4)

    @abstractmethod
    def save_studio_values(self):
        pass

    @abstractmethod
    def save_project_values(self):
        pass

    def set_defaults_state(self):
        self.set_override_state(OverrideState.DEFAULTS)

    def set_studio_state(self):
        self.set_override_state(OverrideState.STUDIO)

    def set_project_state(self):
        self.set_override_state(OverrideState.PROJECT)


class SystemRootEntity(RootEntity):
    def __init__(self, schema_data=None):
        if schema_data is None:
            schema_data = gui_schema("system_schema", "schema_main")
        super(SystemRootEntity, self).__init__(schema_data)

    def _reset_values(self):
        default_value = get_default_settings()[SYSTEM_SETTINGS_KEY]
        for key, child_obj in self.non_gui_children.items():
            value = default_value.get(key, NOT_SET)
            child_obj.update_default_value(value)

        studio_overrides = {}
        studio_overrides = get_studio_system_settings_overrides()
        for key, child_obj in self.non_gui_children.items():
            value = studio_overrides.get(key, NOT_SET)
            child_obj.update_studio_values(value)

    def reset(self, new_state=None):
        if new_state is None:
            new_state = self.override_state

        if new_state is OverrideState.NOT_DEFINED:
            new_state = OverrideState.DEFAULTS

        if new_state is OverrideState.PROJECT:
            raise ValueError("System settings can't store poject overrides.")

        self._reset_values()
        self.set_override_state(new_state)

    def defaults_dir(self):
        return os.path.join(DEFAULTS_DIR, SYSTEM_SETTINGS_KEY)

    def items_are_valid(self):
        # self.validate_duplicated_env_group()
        return True

    def save_studio_values(self):
        # TODO add checks
        settings_value = self.settings_value()
        print(json.dumps(settings_value, indent=4))
        # save_studio_settings(settings_value)

    def save_project_values(self):
        raise ValueError("System settings can't save project overrides.")

    def validate_duplicated_env_group(self, values=None, overrides=None):
        """
        Raises:
            DuplicatedEnvGroups: When value contain duplicated env groups.
        """
        # if overrides is not None:
        #     default_values = get_default_settings()[SYSTEM_SETTINGS_KEY]
        #     values = apply_overrides(default_values, overrides)
        # else:
        #     values = copy.deepcopy(values)
        #
        # # Check if values contain duplicated environment groups
        # find_environments(values)
        pass

    def validate_defaults_to_save(self, value):
        return True
