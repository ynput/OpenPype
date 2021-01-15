import copy
from abc import abstractmethod

from lib import NOT_SET
from constants import WRAPPER_TYPES
from base_entity import BaseEntity, RootEntity, OverrideState


"""
# Abstract properties:
current_value
schema_types
child_has_studio_override
child_value_modified
child_overriden
child_invalid

# Abstract methods:
set_override_state
set_value
update_default_value
update_studio_values
update_project_values
get_invalid
settings_value
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
        # Children are stored by key as keys are immutable and are defined by
        # schema
        self.valid_value_types = (dict, )
        self.children = []
        self.non_gui_children = {}
        self.gui_wrappers = []
        self._add_children(self.schema_data)

    def set_value(self, value):
        for _key, _value in value.items():
            self.non_gui_children[_key].set_value(_value)

    def set_override_state(self, state):
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
    def child_has_studio_override(self):
        pass

    @property
    def child_invalid(self):
        pass

    @property
    def child_value_modified(self):
        pass

    @property
    def child_overriden(self):
        pass

    def discard_changes(self):
        pass

    def get_invalid(self):
        output = []
        for child_obj in self.non_gui_children.values():
            result = child_obj.get_invalid()
            if result:
                output.extend(result)
        return output

    def settings_value(self):
        pass

    def remove_overrides(self):
        pass

    def reset_to_pype_default(self):
        pass

    def set_as_overriden(self):
        pass

    def set_studio_default(self):
        pass

    def update_default_value(self, values):
        for key, child_obj in self.non_gui_children.items():
            child_obj.update_default_value(values[key])

    def update_studio_values(self, parent_values):
        pass

    def update_project_values(self, parent_values):
        pass


class DictMutableKeysEntity(ItemEntity):
    schema_types = ["dict-modifiable"]
    _miss_arg = object()

    def __getitem__(self, key):
        return self.children_by_key[key]

    def __setitem__(self, key, value):
        if key in self.children_by_key:
            self.children_by_key[key].set_value(value)
        else:
            self._add_child(key, value)

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
        return child_obj

    def get(self, key, default=None):
        return self.non_gui_children.get(key, default)

    def keys(self):
        return self.non_gui_children.keys()

    def values(self):
        return self.non_gui_children.values()

    def items(self):
        return self.non_gui_children.items()

    def _add_child(self, key, value):
        new_child = self.create_schema_object(self.item_schema, self, True)

        new_child.set_value(value)

        self.children.append(new_child)
        self.children_by_key[key] = new_child
        return new_child

    def item_initalization(self):
        # Children are stored by key as keys are immutable and are defined by
        # schema
        self.valid_value_types = (dict, )
        self.children = []
        self.children_by_key = {}
        object_type = self.schema_data["object_type"]
        if isinstance(object_type, dict):
            self.item_schema = object_type
        else:
            # Backwards compatibility
            self.item_schema = {
                "type": object_type
            }
            input_modifiers = self.schema_data.get("input_modifiers") or {}
            if input_modifiers:
                self.log.warning((
                    "Used deprecated key `input_modifiers` to define item."
                    " Rather use `object_type` as dictionary with modifiers."
                ))
                self.item_schema.update(input_modifiers)

    def set_value(self, value):
        # TODO cleanup previous keys and values
        pass

    def set_override_state(self, state):
        for child_obj in self.children_by_key.values():
            child_obj.set_override_state(state)

    @property
    def current_value(self):
        output = {}
        for key, child_obj in self.non_gui_children.items():
            output[key] = child_obj.current_value
        return output

    @property
    def child_has_studio_override(self):
        pass

    @property
    def child_invalid(self):
        pass

    @property
    def child_value_modified(self):
        pass

    @property
    def child_overriden(self):
        pass

    def discard_changes(self):
        pass

    def get_invalid(self):
        output = []
        for child_obj in self.non_gui_children.values():
            result = child_obj.get_invalid()
            if result:
                output.extend(result)
        return output

    def settings_value(self):
        pass

    def remove_overrides(self):
        pass

    def reset_to_pype_default(self):
        pass

    def set_as_overriden(self):
        pass

    def set_studio_default(self):
        pass

    def update_default_value(self, parent_values):
        pass

    def update_studio_values(self, parent_values):
        pass

    def update_project_values(self, parent_values):
        pass


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

            child_obj = self.create_schema_object(children_schema, self, True)
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
        # Children are stored by key as keys are immutable and are defined by
        # schema
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
    def child_invalid(self):
        pass

    @property
    def child_value_modified(self):
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
        pass

    def remove_overrides(self):
        pass

    def reset_to_pype_default(self):
        pass

    def set_as_overriden(self):
        pass

    def set_studio_default(self):
        pass

    def update_default_value(self, parent_values):
        pass

    def update_studio_values(self, parent_values):
        pass

    def update_project_values(self, parent_values):
        pass


class InputEntity(ItemEntity):
    def __init__(self, *args, **kwargs):
        super(InputEntity, self).__init__(*args, **kwargs)
        self._current_value = NOT_SET

    def __eq__(self, other):
        if isinstance(other, ItemEntity):
            return self.current_value == other.current_value
        return self.current_value == other

    @property
    def current_value(self):
        return self._current_value

    def update_default_value(self, value):
        self.default_value = value

    def update_project_values(self, value):
        self.studio_override_value = value

    def update_studio_values(self, value):
        self.project_override_value = value

    @property
    def child_has_studio_override(self):
        return self.has_studio_override

    @property
    def child_invalid(self):
        return self.is_invalid

    @property
    def child_value_modified(self):
        return self.value_is_modified

    @property
    def child_overriden(self):
        return self.is_overriden

    def settings_value(self):
        return self.current_value

    def get_invalid(self):
        if self.is_invalid:
            return [self]

    def set_override_state(self, state):
        self.override_state = state
        if (
            state is OverrideState.PROJECT
            and self.project_override_value is not NOT_SET
        ):
            value = self.project_override_value

        elif self.studio_override_value is not NOT_SET:
            value = self.studio_override_value

        else:
            value = self.default_value

        self._current_value = copy.deepcopy(self.default_value)

    def remove_overrides(self):
        current_value = self.default_value
        if self.override_state is OverrideState.STUDIO:
            self.has_studio_override = False

        elif self.override_state is OverrideState.PROJECT:
            self.has_project_override = False
            if self.studio_override_value is not NOT_SET:
                current_value = self.studio_override_value

        self._current_value = current_value

    def reset_to_pype_default(self):
        if self.override_state is OverrideState.PROJECT:
            raise ValueError(
                "Can't reset to Pype defaults on project overrides state."
            )
        self.has_studio_override = False
        self.set_value(self.default_value)

    def set_as_overriden(self):
        self.is_overriden = True

    def set_studio_default(self):
        self.set_value(self.studio_override_value)

    def discard_changes(self):
        self.has_studio_override = self.had_studio_override
        self.has_project_override = self.had_project_override


class GUIEntity(ItemEntity):
    gui_type = True
    schema_types = ["divider", "splitter", "label"]
    child_has_studio_override = False
    child_invalid = False
    child_value_modified = False
    child_overriden = False
    current_value = NOT_SET

    def item_initalization(self):
        self.valid_value_types = tuple()
        self.require_key = False

    def set_value(self, value):
        pass

    def set_override_state(self, state):
        pass

    def discard_changes(self):
        pass

    def get_invalid(self):
        return None

    def settings_value(self):
        pass

    def remove_overrides(self):
        pass

    def reset_to_pype_default(self):
        pass

    def set_as_overriden(self):
        pass

    def set_studio_default(self):
        pass

    def update_default_value(self, parent_values):
        pass

    def update_studio_values(self, parent_values):
        pass

    def update_project_values(self, parent_values):
        pass


class TextEntity(InputEntity):
    schema_types = ["text"]

    def item_initalization(self):
        # Children are stored by key as keys are immutable and are defined by
        # schema
        self.valid_value_types = (str, )

    def set_value(self, value):
        self._current_value = value


class PathEntity(InputEntity):
    schema_types = ["path-widget"]
    platforms = ("windows", "darwin", "linux")

    def item_initalization(self):
        # Children are stored by key as keys are immutable and are defined by
        # schema
        self.multiplatform = self.schema_data.get("multiplatform", False)
        self.multipath = self.schema_data.get("multipath", False)
        self.with_arguments = self.schema_data.get("with_arguments", False)
        if self.multiplatform:
            valid_value_types = (dict, )
        elif self.multipath:
            valid_value_types = (list, )
        else:
            valid_value_types = (str, )

        self.valid_value_types = valid_value_types

    def set_value(self, value):
        if value == self.current_value:
            return

        self._current_value = value
        self.on_value_change()

    def on_value_change(self):
        if self.override_state is OverrideState.STUDIO:
            self.value_is_modified = (
                self.current_value != self.studio_override_value
            )
        elif self.override_state is OverrideState.PROJECT:
            self.value_is_modified = (
                self.current_value != self.project_override_value
            )


class RawJsonEntity(InputEntity):
    schema_types = ["raw-json"]

    def item_initalization(self):
        # Children are stored by key as keys are immutable and are defined by
        # schema
        self.valid_value_types = (list, dict)

    def set_value(self, value):
        self.current_value = value


class NumberEntity(InputEntity):
    schema_types = ["number"]

    def item_initalization(self):
        # Children are stored by key as keys are immutable and are defined by
        # schema
        self.valid_value_types = (int, float)

    def set_value(self, value):
        self.current_value = value


class BoolEntity(InputEntity):
    schema_types = ["boolean"]

    def item_initalization(self):
        # Children are stored by key as keys are immutable and are defined by
        # schema
        self.valid_value_types = (bool, )

    def set_value(self, value):
        self.current_value = value


class EnumEntity(InputEntity):
    schema_types = ["enum"]

    def item_initalization(self):
        # Children are stored by key as keys are immutable and are defined by
        # schema
        self.multiselection = self.schema_data.get("multiselection", False)
        self.enum_items = self.schema_data["enum_items"]
        if not self.enum_items:
            raise ValueError("Attribute `enum_items` is not defined.")

        valid_value_types = set()
        for item in self.enum_items:
            valid_value_types.add(type(item))

        self.valid_value_types = tuple(valid_value_types)

    def set_value(self, value):
        if self.multiselection:
            if not isinstance(value, list):
                if isinstance(value, (set, tuple)):
                    value = list(value)
                else:
                    value = [value]
            check_values = value
        else:
            check_values = [value]

        for item in check_values:
            if item not in self.enum_items:
                raise ValueError(
                    "Invalid value \"{}\". Expected: {}".format(
                        item, self.enum_items
                    )
                )
        self._current_value = value


if __name__ == "__main__":
    from lib import gui_schema
    schema_data = gui_schema("system_schema", "schema_main")
    root = RootEntity(schema_data)
    a = root["general"]["studio_name"]
    print(a.current_value)
