import copy
from abc import abstractmethod

from .lib import NOT_SET
from .constants import (
    OverrideState,
    WRAPPER_TYPES,
    METADATA_KEYS,
    M_OVERRIDEN_KEY,
    M_ENVIRONMENT_KEY,
    M_DYNAMIC_KEY_LABEL
)
from .base_entity import BaseEntity

"""
# TODO
Properties:
- has_defaults
Methods:
- save

# Abstract properties:
## Value of an item no matter if has any overrides (without metadata)
current_value

## Schema types from schemas
schema_types

## TODO change to has_unsaved_changes
has_unsaved_changes
child_is_modified

child_has_studio_override
child_overriden
child_is_invalid

# Abstract methods:
## Trigger update of current values(discard changes) and reseting modifications
set_override_state

## Change current value and trigger modifications and validations of values
- is not for internal value update
set_value

## Return value which will be stored to overrides with metadata
settings_value

## Update values of defaults, studio overrides and project overrides
- these should be used anytime to update values
- current value should be updated if item is without modifications
update_default_value
update_studio_values
update_project_values

## Return invalid item where value is invalid (duplicated keys, invalid value type etc.)
get_invalid

## Item should be able register change callbacks
on_change

## children should notify parent that something has changed
- value has changed
- was set to overriden
- current value has changed
- etc.
on_child_change

## Action calls - last to implement
discard_changes
set_studio_default
reset_to_pype_default
remove_overrides
set_as_overriden
"""


class ItemEntity(BaseEntity):
    def __init__(self, schema_data, parent, is_dynamic_item=False):
        super(ItemEntity, self).__init__(schema_data, parent, is_dynamic_item)

        self.create_schema_object = self.parent.create_schema_object

        self.is_group = schema_data.get("is_group", False)
        self.is_in_dynamic_item = bool(
            not is_dynamic_item
            and (parent.is_dynamic_item or parent.is_in_dynamic_item)
        )

        if not self.is_group and not self.is_in_dynamic_item:
            if self.parent.is_group:
                self.group_item = self.parent
            elif self.parent.group_item:
                self.group_item = self.parent.group_item

        # Dynamic item can't have key defined in it-self
        # - key is defined by it's parent
        if self.is_dynamic_item:
            self.require_key = False

        # If value should be stored to environments
        self.env_group_key = schema_data.get("env_group_key")
        self.is_env_group = bool(self.env_group_key is not None)

        roles = schema_data.get("roles")
        if roles is None:
            roles = parent.roles
        elif not isinstance(roles, list):
            roles = [roles]
        self.roles = roles

        # States of inputs
        # QUESTION has usage in entity?
        self.state = None

        self.key = schema_data.get("key")
        self.label = schema_data.get("label")

        self.item_initalization()

        if self.valid_value_types is NOT_SET:
            raise ValueError("Attribute `valid_value_types` is not filled.")

        if self.require_key and not self.key:
            error_msg = "Missing \"key\" in schema data. {}".format(
                str(schema_data).replace("'", '"')
            )
            raise KeyError(error_msg)

        if not self.label and self.is_group:
            raise ValueError(
                "Item is set as `is_group` but has empty `label`."
            )

    @abstractmethod
    def item_initalization(self):
        pass


class GUIEntity(ItemEntity):
    gui_type = True

    schema_types = ["divider", "splitter", "label"]
    child_has_studio_override = False
    child_is_invalid = False
    has_unsaved_changes = False
    child_is_modified = False
    child_overriden = False
    current_value = NOT_SET

    # Abstract methods
    set_value = None
    set_override_state = None
    discard_changes = None
    on_change = None
    on_child_change = None
    on_value_change = None
    get_invalid = None
    settings_value = None
    remove_overrides = None
    reset_to_pype_default = None
    set_as_overriden = None
    set_studio_default = None
    update_default_value = None
    update_studio_values = None
    update_project_values = None

    def item_initalization(self):
        self.valid_value_types = tuple()
        self.require_key = False


class DictImmutableKeysEntity(ItemEntity):
    schema_types = ["dict"]

    def __getitem__(self, key):
        return self.non_gui_children[key]

    def __setitem__(self, key, value):
        child_obj = self.non_gui_children[key]
        child_obj.set_value(value)

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

    def on_value_change(self):
        raise NotImplementedError(
            "{} - on_value_change".format(self.__class__.__name__)
        )

    def on_change(self):
        # TODO implement
        pass

    def on_child_change(self, child_obj):
        # TODO implement
        print("{} on_child_change not yet implemented".format(
            self.__class__.__name__
        ))

    def _add_children(self, schema_data, first=True):
        added_children = []
        for children_schema in schema_data["children"]:
            if children_schema["type"] in WRAPPER_TYPES:
                _children_schema = copy.deepcopy(children_schema)
                wrapper_children = self._add_children(
                    children_schema
                )
                _children_schema["children"] = wrapper_children
                added_children.append(_children_schema)
                continue

            child_obj = self.create_schema_object(children_schema, self)
            self.children.append(child_obj)
            added_children.append(child_obj)
            if isinstance(child_obj, GUIEntity):
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
        self.default_metadata = {}
        self.studio_override_metadata = {}
        self.project_override_metadata = {}

        # current_metadata are still when schema is loaded
        self.current_metadata = {}

        # Children are stored by key as keys are immutable and are defined by
        # schema
        self.valid_value_types = (dict, )
        self.children = []
        self.non_gui_children = {}
        self.gui_wrappers = []
        self._add_children(self.schema_data)

        if not self.is_group and not self.group_item:
            groups = []
            for key, child_obj in self.non_gui_children.items():
                if child_obj.is_group:
                    groups.append(key)

            if groups:
                self.current_metadata[M_OVERRIDEN_KEY] = groups

        if self.is_dynamic_item:
            self.require_key = False

    def set_value(self, value):
        for _key, _value in value.items():
            self.non_gui_children[_key].set_value(_value)

    def set_override_state(self, state):
        # TODO change metadata
        self.override_state = state
        for child_obj in self.non_gui_children.values():
            child_obj.set_override_state(state)

    @property
    def current_value(self):
        output = {}
        for key, child_obj in self.non_gui_children.items():
            output[key] = child_obj.current_value
        return output

    @property
    def has_unsaved_changes(self):
        if (
            self.override_state is OverrideState.PROJECT
            and self.has_project_override != self.had_project_override
        ):
            return True

        elif (
            self.override_state is OverrideState.STUDIO
            and self.has_studio_override != self.had_studio_override
        ):
            return True

        return self.child_is_modified

    @property
    def child_is_modified(self):
        for child_obj in self.non_gui_children.values():
            if child_obj.has_unsaved_changes:
                return True
        return False

    @property
    def child_has_studio_override(self):
        pass

    @property
    def child_is_invalid(self):
        pass

    @property
    def child_overriden(self):
        pass

    def get_invalid(self):
        output = []
        for child_obj in self.non_gui_children.values():
            result = child_obj.get_invalid()
            if result:
                output.extend(result)
        return output

    def settings_value(self):
        # If is in dynamic item then any metadata are irrelevant
        if self.is_dynamic_item or self.is_in_dynamic_item:
            return self.current_value

        if not self.group_item:
            if not self.has_unsaved_changes and not self.child_is_modified:
                return NOT_SET

        output = {}
        any_is_set = False
        for key, child_obj in self.non_gui_children.items():
            value = child_obj.settings_value()
            if value is not NOT_SET:
                output[key] = value
                any_is_set = True

        if any_is_set:
            return output
        return NOT_SET

    def _prepare_value(self, value):
        metadata = {}
        if isinstance(value, dict):
            for key in METADATA_KEYS:
                if key in value:
                    metadata[key] = value.pop(key)
        return value, metadata

    def update_default_value(self, value):
        value, metadata = self._prepare_value(value)
        self.default_metadata = metadata

        if value is NOT_SET:
            for child_obj in self.non_gui_children.values():
                child_obj.update_default_value(value)
            return

        for _key, _value in value.items():
            child_obj = self.non_gui_children.get(_key)
            if child_obj:
                child_obj.update_project_values(_value)
            else:
                # TODO store that has unsaved changes if is group item or
                # is inside group item
                self.log.warning(
                    "Unknown key in default values \"{}\"".format(_key)
                )

    def update_studio_values(self, value):
        value, metadata = self._prepare_value(value)
        self.studio_override_metadata = metadata

        if value is NOT_SET:
            for child_obj in self.non_gui_children.values():
                child_obj.update_studio_values(value)
            return

        for _key, _value in value.items():
            child_obj = self.non_gui_children.get(_key)
            if child_obj:
                child_obj.update_studio_values(_value)
            else:
                # TODO store that has unsaved changes if is group item or
                # is inside group item
                self.log.warning(
                    "Unknown key in studio overrides \"{}\"".format(_key)
                )

    def update_project_values(self, value):
        value, metadata = self._prepare_value(value)
        self.project_override_metadata = metadata

        if value is NOT_SET:
            for child_obj in self.non_gui_children.values():
                child_obj.update_project_values(value)
            return

        for _key, _value in value.items():
            child_obj = self.non_gui_children.get(_key)
            if child_obj:
                child_obj.update_project_values(_value)
            else:
                # TODO store that has unsaved changes if is group item or
                # is inside group item
                self.log.warning(
                    "Unknown key in project overrides \"{}\"".format(_key)
                )

    def discard_changes(self):
        pass

    def remove_overrides(self):
        pass

    def reset_to_pype_default(self):
        pass

    def set_as_overriden(self):
        pass

    def set_studio_default(self):
        pass


class DictMutableKeysEntity(ItemEntity):
    schema_types = ["dict-modifiable"]
    _miss_arg = object()

    def __getitem__(self, key):
        return self.children_by_key[key]

    def __setitem__(self, key, value):
        self.set_value_for_key(key, value)

    def __iter__(self):
        for key in self.keys():
            yield key

    def pop(self, key, default=_miss_arg):
        if key not in self.children_by_key:
            if default is self._miss_arg:
                raise KeyError("Key \"{}\" not found.".format(key))
            return default

        child_obj = self.children_by_key.pop(key)
        self.children.remove(child_obj)
        self.on_value_change()
        return child_obj

    def get(self, key, default=None):
        return self.children_by_key.get(key, default)

    def keys(self):
        return self.children_by_key.keys()

    def values(self):
        return self.children_by_key.values()

    def items(self):
        return self.children_by_key.items()

    def clear(self):
        for key in tuple(self.children_by_key.keys()):
            self.pop(key)

    def _add_child(self, key):
        new_child = self.create_schema_object(self.item_schema, self, True)
        self.children.append(new_child)
        self.children_by_key[key] = new_child
        return new_child

    def item_initalization(self):
        self.default_metadata = {}
        self.studio_override_metadata = {}
        self.project_override_metadata = {}

        # current_metadata are still when schema is loaded
        self.current_metadata = {}

        self.valid_value_types = (dict, )
        self.children = []
        self.children_by_key = {}
        self._current_value = NOT_SET

        object_type = self.schema_data["object_type"]
        if not isinstance(object_type, dict):
            # Backwards compatibility
            object_type = {
                "type": object_type
            }
            input_modifiers = self.schema_data.get("input_modifiers") or {}
            if input_modifiers:
                self.log.warning((
                    "Used deprecated key `input_modifiers` to define item."
                    " Rather use `object_type` as dictionary with modifiers."
                ))
                object_type.update(input_modifiers)
        self.item_schema = object_type

    def set_value_for_key(self, key, value, batch=False):
        # TODO Check for value type if is Settings entity?
        child_obj = self.children_by_key.get(key)
        if not child_obj:
            child_obj = self._add_child(key)

        child_obj.set_value(value)

        if not batch:
            self.on_value_change()

    def on_change(self):
        # TODO implement
        pass

    def on_child_change(self, child_obj):
        # TODO implement
        print("{} on_child_change not yet implemented".format(
            self.__class__.__name__
        ))

    def _metadata_for_current_state(self):
        if (
            self.override_state is OverrideState.PROJECT
            and self.project_override_value is not NOT_SET
        ):
            previous_metadata = self.project_override_value

        elif self.studio_override_value is not NOT_SET:
            previous_metadata = self.studio_override_metadata
        else:
            previous_metadata = self.default_metadata
        return copy.deepcopy(previous_metadata)

    def get_metadata_from_value(self, value, previous_metadata=None):
        """Get metada for entered value.

        Method may modify entered value object in case that contain .
        """
        metadata = {}
        if not isinstance(value, dict):
            return metadata

        # Fill label metadata
        # - first check if value contain them
        if M_DYNAMIC_KEY_LABEL in value:
            metadata[M_DYNAMIC_KEY_LABEL] = value.pop(M_DYNAMIC_KEY_LABEL)

        # - check if metadata for current state contain metadata
        elif M_DYNAMIC_KEY_LABEL in previous_metadata:
            # Get previous metadata fo current state if were not entered
            if previous_metadata is None:
                previous_metadata = self._metadata_for_current_state()
            # Create copy to not affect data passed with arguments
            label_metadata = copy.deepcopy(
                previous_metadata[M_DYNAMIC_KEY_LABEL]
            )
            for key in tuple(label_metadata.keys()):
                if key not in value:
                    label_metadata.pop(key)

            metadata[M_DYNAMIC_KEY_LABEL] = label_metadata

        # Pop all other metadata keys from value
        for key in METADATA_KEYS:
            if key in value:
                value.pop(key)

        # Add environment metadata
        if self.is_env_group:
            metadata[M_ENVIRONMENT_KEY] = {
                self.env_group_key: list(value.keys())
            }
        return metadata

    def set_value(self, value):
        for _key, _value in value.items():
            self.set_value_for_key(_key, _value, True)
        self.on_value_change()

    def set_override_state(self, state):
        # TODO change metadata
        self.override_state = state
        using_overrides = True
        if (
            state is OverrideState.PROJECT
            and self.project_override_value is not NOT_SET
        ):
            value = self.project_override_value
            metadata = self.project_override_metadata

        elif self.studio_override_value is not NOT_SET:
            value = self.studio_override_value
            metadata = self.studio_override_metadata

        else:
            using_overrides = False
            value = self.default_value
            metadata = self.default_metadata

        # TODO REQUIREMENT value must be stored to _current_value
        # - current value must not be dynamic!!!
        # - it is required to update metadata on the fly
        new_value = copy.deepcopy(value)
        self._current_value = new_value
        # It is important to pass `new_value`!!!
        self.current_metadata = self.get_metadata_from_value(
            new_value, metadata
        )

        # Simulate `clear` method without triggering value change
        for key in tuple(self.children_by_key.keys()):
            child_obj = self.children_by_key.pop(key)
            self.children.remove(child_obj)

        # Create new children
        for _key, _value in self._current_value.items():
            child_obj = self._add_child(_key)
            child_obj.update_default_value(_value)
            if using_overrides:
                if state is OverrideState.STUDIO:
                    child_obj.update_studio_values(value)
                else:
                    child_obj.update_project_values(value)

            child_obj.set_override_state(state)

    @property
    def current_value(self):
        output = {}
        for key, child_obj in self.children_by_key.items():
            output[key] = child_obj.current_value
        return output

    @property
    def has_unsaved_changes(self):
        pass

    @property
    def child_has_studio_override(self):
        pass

    @property
    def child_is_invalid(self):
        pass

    @property
    def child_is_modified(self):
        pass

    @property
    def child_overriden(self):
        pass

    def discard_changes(self):
        pass

    def get_invalid(self):
        output = []
        for child_obj in self.children_by_key.values():
            result = child_obj.get_invalid()
            if result:
                output.extend(result)
        return output

    def settings_value(self):
        output = {}
        for key, child_obj in self.children_by_key.items():
            output[key] = child_obj.settings_value()
        return output

    def remove_overrides(self):
        pass

    def reset_to_pype_default(self):
        pass

    def set_as_overriden(self):
        pass

    def set_studio_default(self):
        pass

    def _prepare_value(self, value):
        metadata = {}
        if isinstance(value, dict):
            for key in METADATA_KEYS:
                if key in value:
                    metadata[key] = value.pop(key)
        return value, metadata

    def update_default_value(self, value):
        value, metadata = self._prepare_value(value)
        self.default_value = value
        self.default_metadata = metadata

    def update_studio_values(self, value):
        value, metadata = self._prepare_value(value)
        self.project_override_value = value
        self.studio_override_metadata = metadata

    def update_project_values(self, value):
        value, metadata = self._prepare_value(value)
        self.studio_override_value = value
        self.project_override_metadata = metadata


class ListEntity(ItemEntity):
    schema_types = ["list"]

    def __iter__(self):
        pass

    def append(self, item):
        pass

    def extend(self, items):
        pass

    def clear(self):
        pass

    def pop(self, idx):
        pass

    def remove(self, item):
        pass

    def insert(self, idx, item):
        pass

    def reverse(self):
        pass

    def sort(self):
        pass

    def _add_children(self):
        child_obj = self.create_schema_object(self.item_schema, self, True)
        self.children.append(child_obj)
        return child_obj

    def item_initalization(self):
        self.valid_value_types = (list, )
        self.children = []

        item_schema = self.schema_data["object_type"]
        if not isinstance(item_schema, dict):
            item_schema = {"type": item_schema}
        self.item_schema = item_schema

        # GUI attributes
        self.use_label_wrap = self.schema_data.get("use_label_wrap") or False
        # Used only if `use_label_wrap` is set to True
        self.collapsible = self.schema_data.get("collapsible") or True
        self.collapsed = self.schema_data.get("collapsed") or False

    def set_value(self, value):
        pass

    def on_change(self):
        pass

    def on_child_change(self, child_obj):
        print("{} - on_child_change".format(self.__class__.__name__))

    def on_value_change(self):
        raise NotImplementedError(self.__class__.__name__)

    def set_override_state(self, state):
        for child_obj in self.children:
            child_obj.set_override_state(state)

    @property
    def current_value(self):
        output = []
        for child_obj in self.children:
            output.append(child_obj.current_value)
        return output

    @property
    def child_has_studio_override(self):
        pass

    @property
    def child_is_invalid(self):
        pass

    @property
    def has_unsaved_changes(self):
        pass

    @property
    def child_is_modified(self):
        pass

    @property
    def child_overriden(self):
        pass

    def discard_changes(self):
        pass

    def get_invalid(self):
        output = []
        for child_obj in self.children:
            result = child_obj.get_invalid()
            if result:
                output.extend(result)
        return output

    def settings_value(self):
        if self.is_in_dynamic_item:
            return self.current_value

        if not self.has_unsaved_changes:
            return NOT_SET

        output = []
        for child_obj in self.children:
            output.append(child_obj.settings_value())
        return output

    def remove_overrides(self):
        pass

    def reset_to_pype_default(self):
        pass

    def set_as_overriden(self):
        pass

    def set_studio_default(self):
        pass

    def update_default_value(self, value):
        pass

    def update_studio_values(self, value):
        pass

    def update_project_values(self, value):
        pass


class PathEntity(ItemEntity):
    schema_types = ["path-widget"]
    platforms = ("windows", "darwin", "linux")
    platform_labels_mapping = {
        "windows": "Windows",
        "darwin": "MacOS",
        "linux": "Linux"
    }
    path_item_type_error = "Got invalid path value type {}. Expected: {}"

    def __setitem__(self, *args, **kwargs):
        return self.child_obj.__setitem__(*args, **kwargs)

    def __getitem__(self, *args, **kwargs):
        return self.child_obj.__getitem__(*args, **kwargs)

    def __iter__(self):
        return self.child_obj.__iter__()

    def keys(self):
        return self.child_obj.keys()

    def values(self):
        return self.child_obj.values()

    def items(self):
        return self.child_obj.items()

    def item_initalization(self):
        self.multiplatform = self.schema_data.get("multiplatform", False)
        self.multipath = self.schema_data.get("multipath", False)
        self.with_arguments = self.schema_data.get("with_arguments", False)

        # Create child object
        if not self.multiplatform and not self.multipath:
            valid_value_types = (str, )
            item_schema = {
                "type": "path-input",
                "key": self.key,
                "with_arguments": self.with_arguments
            }

        elif not self.multiplatform:
            valid_value_types = (list, )
            item_schema = {
                "type": "list",
                "key": self.key,
                "object_type": {
                    "type": "path-input",
                    "with_arguments": self.with_arguments
                }
            }

        else:
            valid_value_types = (dict, )
            item_schema = {
                "type": "dict",
                "key": self.key,
                "show_borders": False,
                "children": []
            }
            for platform_key in self.platforms:
                platform_label = self.platform_labels_mapping[platform_key]
                child_item = {
                    "key": platform_key,
                    "label": platform_label
                }
                if self.multipath:
                    child_item["type"] = "list"
                    child_item["object_type"] = {
                        "type": "path-input",
                        "with_arguments": self.with_arguments
                    }
                else:
                    child_item["type"] = "path-input"
                    child_item["with_arguments"] = self.with_arguments

                item_schema["children"].append(child_item)

        self.child_obj = self.create_schema_object(item_schema, self)
        self.valid_value_types = valid_value_types

    def set_value(self, value):
        self.child_obj.set_value(value)

    def settings_value(self):
        value = self.child_obj.settings_value()
        if value is not NOT_SET and self.multiplatform:
            value = self.child_obj.current_value
        return value

    def on_value_change(self):
        raise NotImplementedError(self.__class__.__name__)

    def on_change(self):
        pass

    def on_child_change(self, child_obj):
        print("{} - on_child_change".format(self.__class__.__name__))

    @property
    def child_has_studio_override(self):
        return self.child_obj.child_has_studio_override

    @property
    def child_is_invalid(self):
        return self.child_obj.child_is_invalid

    @property
    def child_is_modified(self):
        return self.child_obj.child_is_modified

    @property
    def child_overriden(self):
        return self.child_obj.child_overriden

    @property
    def current_value(self):
        return self.child_obj.current_value

    def get_invalid(self):
        return None

    def has_unsaved_changes(self):
        pass

    def discard_changes(self):
        self.child_obj.discard_changes()

    def remove_overrides(self):
        self.child_obj.remove_overrides()

    def reset_to_pype_default(self):
        self.child_obj.reset_to_pype_default()

    def set_as_overriden(self):
        self.child_obj.set_as_overriden()

    def set_override_state(self, state):
        self.child_obj.set_override_state(state)

    def set_studio_default(self):
        pass

    def update_default_value(self, value):
        self.child_obj.update_default_value(value)

    def update_project_values(self, value):
        self.child_obj.update_project_values(value)

    def update_studio_values(self, value):
        self.child_obj.update_studio_values(value)


class ListStrictEntity(_NotImplemented):
    schema_types = ["list-strict"]

    gui_type = True

    child_has_studio_override = False
    child_is_invalid = False
    has_unsaved_changes = False
    child_is_modified = False
    child_overriden = False
    current_value = NOT_SET

    # Abstract methods
    set_value = None
    set_override_state = None
    discard_changes = None
    on_change = None
    on_child_change = None
    on_value_change = None
    get_invalid = None
    settings_value = None
    remove_overrides = None
    reset_to_pype_default = None
    set_as_overriden = None
    set_studio_default = None
    update_default_value = None
    update_studio_values = None
    update_project_values = None

    def item_initalization(self):
        self.valid_value_types = (list, )
        self.require_key = False
