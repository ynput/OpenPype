from abc import abstractmethod

from .lib import (
    NOT_SET,
    OverrideState,
    DefaultsNotDefined,
    SchemeGroupHierarchyBug
)

from .base_entity import BaseEntity

"""
# TODO
Methods:
- save

# Properties
## Value attributes - should be set on `set_override_state` based on updated
    values
has_defaults
has_studio_override
had_studio_override
has_project_override
had_project_override

# Abstract properties:
## Value of an item no matter if has any overrides (without metadata)
value

## Schema types from schemas
schema_types

## Unsaved changes
has_unsaved_changes
child_is_modified

child_has_studio_override
child_has_project_override

# Abstract methods:
## Trigger update of current values(discard changes) and reseting modifications
set_override_state

## Change current value and trigger modifications and validations of values
- is not for internal value update
set

## Return value which will be stored to overrides with metadata
settings_value

## Update values of defaults, studio overrides and project overrides
- these should be used anytime to update values
- current value should be updated if item is without modifications
update_default_value
update_studio_values
update_project_values

## Item should be able register change callbacks
on_change

## children should notify parent that something has changed
- value has changed
- was set to overriden
- current value has changed
- etc.
on_child_change

## Save settings
save

## Action calls - last to implement
discard_changes
add_to_studio_default
remove_from_studio_default
remove_overrides
set_as_overriden
"""


class ItemEntity(BaseEntity):
    def __init__(self, schema_data, parent, is_dynamic_item=False):
        super(ItemEntity, self).__init__(schema_data, parent, is_dynamic_item)

        self.create_schema_object = self.parent.create_schema_object

        self.is_file = schema_data.get("is_file", False)
        self.is_group = schema_data.get("is_group", False)
        self.is_in_dynamic_item = bool(
            not is_dynamic_item
            and (parent.is_dynamic_item or parent.is_in_dynamic_item)
        )

        # Root item reference
        self.root_item = self.parent.root_item

        # File item reference
        if self.parent.is_file:
            self.file_item = self.parent
        elif self.parent.file_item:
            self.file_item = self.parent.file_item

        # Group item reference
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

    def schema_validations(self):
        if self.valid_value_types is NOT_SET:
            raise ValueError("Attribute `valid_value_types` is not filled.")

        if self.require_key and not self.key:
            error_msg = "{}: Missing \"key\" in schema data. {}".format(
                self.path, str(self.schema_data).replace("'", '"')
            )
            raise KeyError(error_msg)

        if not self.label and self.is_group:
            raise ValueError(
                "{}: Item is set as `is_group` but has empty `label`.".format(
                    self.path
                )
            )

        if self.is_group and self.group_item:
            raise SchemeGroupHierarchyBug(self.path)

        if not self.file_item and self.is_env_group:
            raise ValueError((
                "{}: Environment item is not inside file"
                " item so can't store metadata for defaults."
            ).format(self.path))

        if self.label and self.is_dynamic_item:
            raise ValueError((
                "{}: Item has set label but is used as dynamic item."
            ).format(self.path))

    @abstractmethod
    def item_initalization(self):
        pass

    def save(self):
        """Call save on root item."""
        self.root_item.save()


class GUIEntity(ItemEntity):
    gui_type = True

    schema_types = ["divider", "splitter", "label"]
    child_has_studio_override = False
    has_unsaved_changes = False
    child_is_modified = False
    child_has_project_override = False
    value = NOT_SET

    path = "GUIEntity"

    # Abstract methods
    get_child_path = None
    set = None
    set_override_state = None
    settings_value = None
    on_change = None
    on_child_change = None

    _discard_changes = None
    _remove_from_studio_default = None
    _remove_overrides = None
    set_as_overriden = None
    add_to_studio_default = None
    update_default_value = None
    update_studio_values = None
    update_project_values = None

    def __getitem__(self, key):
        return self.schema_data[key]

    def schema_validations(self):
        return

    def item_initalization(self):
        self.valid_value_types = tuple()
        self.require_key = False


class PathEntity(ItemEntity):
    schema_types = ["path-widget"]
    platforms = ("windows", "darwin", "linux")
    platform_labels_mapping = {
        "windows": "Windows",
        "darwin": "MacOS",
        "linux": "Linux"
    }
    path_item_type_error = "Got invalid path value type {}. Expected: {}"
    attribute_error_msg = (
        "'PathEntity' has no attribute '{}' if is not set as multiplatform"
    )

    def __setitem__(self, *args, **kwargs):
        return self.child_obj.__setitem__(*args, **kwargs)

    def __getitem__(self, *args, **kwargs):
        return self.child_obj.__getitem__(*args, **kwargs)

    def __iter__(self):
        return self.child_obj.__iter__()

    def keys(self):
        if not self.multiplatform:
            raise AttributeError(self.attribute_error_msg.format("keys"))
        return self.child_obj.keys()

    def values(self):
        if not self.multiplatform:
            raise AttributeError(self.attribute_error_msg.format("values"))
        return self.child_obj.values()

    def items(self):
        if not self.multiplatform:
            raise AttributeError(self.attribute_error_msg.format("items"))
        return self.child_obj.items()

    def item_initalization(self):
        if not self.group_item and not self.is_group:
            self.is_group = True

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

        self.valid_value_types = valid_value_types
        self.child_obj = self.create_schema_object(item_schema, self)

    def get_child_path(self, _child_obj):
        return self.path

    def set(self, value):
        self.child_obj.set(value)

    def settings_value(self):
        if self.override_state is OverrideState.NOT_DEFINED:
            return NOT_SET

        if self.is_group:
            if self.override_state is OverrideState.STUDIO:
                if not self.has_studio_override:
                    return NOT_SET
            elif self.override_state is OverrideState.PROJECT:
                if not self.has_project_override:
                    return NOT_SET

        return self.child_obj.settings_value()

    def on_change(self):
        for callback in self.on_change_callbacks:
            callback()
        self.parent.on_child_change(self)

    def on_child_change(self, _child_obj):
        if self.override_state is OverrideState.STUDIO:
            self._has_studio_override = self.child_has_studio_override
        elif self.override_state is OverrideState.PROJECT:
            self._has_project_override = self.child_has_project_override
        self.on_change()

    @property
    def child_has_studio_override(self):
        return self.child_obj.child_has_studio_override

    @property
    def child_is_modified(self):
        return self.child_obj.child_is_modified

    @property
    def child_has_project_override(self):
        return self.child_obj.child_has_project_override

    @property
    def value(self):
        return self.child_obj.value

    @property
    def has_unsaved_changes(self):
        return self.child_obj.has_unsaved_changes

    def set_override_state(self, state):
        self.override_state = state
        self.child_obj.set_override_state(state)

    def update_default_value(self, value):
        self.child_obj.update_default_value(value)

    def update_project_values(self, value):
        self.child_obj.update_project_values(value)

    def update_studio_values(self, value):
        self.child_obj.update_studio_values(value)

    def _discard_changes(self, *args):
        self.child_obj.discard_changes(*args)

    def add_to_studio_default(self):
        self.child_obj.add_to_studio_default()

    def _remove_from_studio_default(self, *args):
        self.child_obj.remove_from_studio_default(*args)
        self._has_studio_override = False

    def _remove_overrides(self, *args):
        self.child_obj.remove_overrides(*args)
        self._has_project_override = False

    def set_as_overriden(self):
        self.child_obj.set_as_overriden()

    def reset_callbacks(self):
        super(PathEntity, self).reset_callbacks()
        self.child_obj.reset_callbacks()


class ListStrictEntity(ItemEntity):
    schema_types = ["list-strict"]

    def item_initalization(self):
        self.valid_value_types = (list, )
        self.require_key = True

        self.initial_value = None

        self.ignore_child_changes = False

        # Child items
        self.object_types = self.schema_data["object_types"]

        self.children = []
        for children_schema in self.object_types:
            child_obj = self.create_schema_object(children_schema, self, True)
            self.children.append(child_obj)

        # GUI attribute
        self.is_horizontal = self.schema_data.get("horizontal", True)
        if not self.group_item and not self.is_group:
            self.is_group = True

    def get_child_path(self, child_obj):
        result_idx = None
        for idx, _child_obj in enumerate(self.children):
            if _child_obj is child_obj:
                result_idx = idx
                break

        if result_idx is None:
            raise ValueError("Didn't found child {}".format(child_obj))

        return "/".join([self.path, str(result_idx)])

    @property
    def value(self):
        output = []
        for child_obj in self.children:
            output.append(child_obj.value)
        return output

    def set(self, value):
        for idx, item in value:
            self.children[idx].set(item)

    def settings_value(self):
        output = []
        for child_obj in self.children:
            output.append(child_obj.settings_value())
        return output

    def on_change(self):
        for callback in self.on_change_callbacks:
            callback()
        self.parent.on_child_change(self)

    def on_child_change(self, _child_obj):
        if self.ignore_child_changes:
            return

        if self.override_state is OverrideState.STUDIO:
            self._has_studio_override = self.child_has_studio_override
        elif self.override_state is OverrideState.PROJECT:
            self._has_project_override = self.child_has_project_override

        self.on_change()

    def has_unsaved_changes(self):
        if self.override_state is OverrideState.NOT_DEFINED:
            return False

        if self.override_state is OverrideState.DEFAULTS:
            if not self.has_default_value:
                return True

        elif self.override_state is OverrideState.STUDIO:
            if self.had_studio_override != self._has_studio_override:
                return True

            if not self._has_studio_override and not self.has_default_value:
                return True

        elif self.override_state is OverrideState.PROJECT:
            if self.had_project_override != self._has_project_override:
                return True

            if (
                not self._has_project_override
                and not self._has_studio_override
                and not self.has_default_value
            ):
                return True

        if self.child_is_modified:
            return True

        if self.settings_value() != self.initial_value:
            return True
        return False

    def child_is_modified(self):
        for child_obj in self.children:
            if child_obj.has_unsaved_changes:
                return True
        return False

    def child_has_studio_override(self):
        for child_obj in self.children:
            if child_obj.has_studio_override:
                return True
        return False

    def child_has_project_override(self):
        for child_obj in self.children:
            if child_obj.has_project_override:
                return True
        return False

    def set_override_state(self, state):
        self.override_state = state
        if not self.has_default_value and state > OverrideState.DEFAULTS:
            # Ignore if is dynamic item and use default in that case
            if not self.is_dynamic_item and not self.is_in_dynamic_item:
                raise DefaultsNotDefined(self)

        for child_obj in self.children:
            child_obj.set_override_state(state)

        self.initial_value = self.settings_value()

    def _discard_changes(self, on_change_trigger):
        for child_obj in self.children:
            child_obj.discard_changes(on_change_trigger)

    def add_to_studio_default(self):
        if self.override_state is not OverrideState.STUDIO:
            return
        self._has_studio_override = True
        self.on_change()

    def _remove_from_studio_default(self, on_change_trigger):
        self.ignore_child_changes = True

        for child_obj in self.children:
            child_obj.remove_from_studio_default(on_change_trigger)

        self.ignore_child_changes = False

        self._has_studio_override = False

    def set_as_overriden(self):
        self._has_project_override = True
        self.on_change()

    def _remove_overrides(self, on_change_trigger):
        if self.override_state is not OverrideState.PROJECT:
            return

        self.ignore_child_changes = True

        for child_obj in self.children:
            child_obj.remove_overrides(on_change_trigger)

        self.ignore_child_changes = False

        self._has_project_override = False

    def check_update_value(self, value, value_type):
        value = super(ListStrictEntity, self).check_update_value(
            value, value_type
        )
        if value is NOT_SET:
            return value

        child_len = len(self.children)
        value_len = len(value)
        if value_len == child_len:
            return value

        self.log.warning(
            (
                "{} Amount of strict list items in {} values is"
                " not same as expected. Expected {} items. Got {} items. {}"
            ).format(
                self.path, value_type,
                child_len, value_len, str(value)
            )
        )

        if value_len < child_len:
            # Fill missing values with NOT_SET
            for _ in range(child_len - value_len):
                value.append(NOT_SET)
        else:
            # Pop values that are overloaded
            for _ in range(value_len - child_len):
                value.pop(child_len)
        return value

    def update_default_value(self, value):
        value = self.check_update_value(value, "default")
        self.has_default_value = value is not NOT_SET
        if value is NOT_SET:
            for child_obj in self.children:
                child_obj.update_default_value(value)

        else:
            for idx, item_value in enumerate(value):
                self.children[idx].update_default_value(item_value)

    def update_studio_values(self, value):
        value = self.check_update_value(value, "studio override")
        if value is NOT_SET:
            for child_obj in self.children:
                child_obj.update_studio_values(value)

        else:
            for idx, item_value in enumerate(value):
                self.children[idx].update_studio_values(item_value)

    def update_project_values(self, value):
        value = self.check_update_value(value, "project override")
        if value is NOT_SET:
            for child_obj in self.children:
                child_obj.update_project_values(value)

        else:
            for idx, item_value in enumerate(value):
                self.children[idx].update_project_values(item_value)

    def reset_callbacks(self):
        super(ListStrictEntity, self).reset_callbacks()
        self.child_obj.reset_callbacks()
