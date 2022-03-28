import re

import six

from .lib import (
    NOT_SET,
    STRING_TYPE,
    OverrideState
)
from .exceptions import (
    DefaultsNotDefined,
    StudioDefaultsNotDefined,
    EntitySchemaError
)
from .base_entity import ItemEntity


class PathEntity(ItemEntity):
    schema_types = ["path"]
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

    def has_child_with_key(self, key):
        return self.child_obj.has_child_with_key(key)

    def _item_initialization(self):
        if self.group_item is None and not self.is_group:
            self.is_group = True

        self.multiplatform = self.schema_data.get("multiplatform", False)
        self.multipath = self.schema_data.get("multipath", False)

        placeholder_text = self.schema_data.get("placeholder")

        # Create child object
        if not self.multiplatform and not self.multipath:
            valid_value_types = (STRING_TYPE, )
            item_schema = {
                "type": "path-input",
                "key": self.key,
                "placeholder": placeholder_text
            }

        elif not self.multiplatform:
            valid_value_types = (list, )
            item_schema = {
                "type": "list",
                "key": self.key,
                "object_type": {
                    "type": "path-input",
                    "placeholder": placeholder_text
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
                        "placeholder": placeholder_text
                    }
                else:
                    child_item["type"] = "path-input"
                    child_item["placeholder"] = placeholder_text

                item_schema["children"].append(child_item)

        self.valid_value_types = valid_value_types
        self.child_obj = self.create_schema_object(item_schema, self)

    def collect_static_entities_by_path(self):
        return self.child_obj.collect_static_entities_by_path()

    def get_child_path(self, _child_obj):
        return self.path

    def set(self, value):
        self.child_obj.set(value)

    def collect_dynamic_schema_entities(self, *args, **kwargs):
        self.child_obj.collect_dynamic_schema_entities(*args, **kwargs)

    def settings_value(self):
        if self._override_state is OverrideState.NOT_DEFINED:
            return NOT_SET

        if self.is_group:
            if self._override_state is OverrideState.STUDIO:
                if not self.has_studio_override:
                    return NOT_SET
            elif self._override_state is OverrideState.PROJECT:
                if not self.has_project_override:
                    return NOT_SET

        return self.child_obj.settings_value()

    def on_change(self):
        for callback in self.on_change_callbacks:
            callback()
        self.parent.on_child_change(self)

    def on_child_change(self, _child_obj):
        self.on_change()

    @property
    def has_unsaved_changes(self):
        return self.child_obj.has_unsaved_changes

    @property
    def has_studio_override(self):
        return self.child_obj.has_studio_override

    @property
    def has_project_override(self):
        return self.child_obj.has_project_override

    @property
    def value(self):
        return self.child_obj.value

    def set_override_state(self, state, ignore_missing_defaults):
        # Trigger override state change of root if is not same
        if self.root_item.override_state is not state:
            self.root_item.set_override_state(state)
            return

        self._override_state = state
        self._ignore_missing_defaults = ignore_missing_defaults
        self.child_obj.set_override_state(state, ignore_missing_defaults)

    def update_default_value(self, value, log_invalid_types=True):
        self._default_log_invalid_types = log_invalid_types
        self.child_obj.update_default_value(value, log_invalid_types)

    def update_project_value(self, value, log_invalid_types=True):
        self._studio_log_invalid_types = log_invalid_types
        self.child_obj.update_project_value(value, log_invalid_types)

    def update_studio_value(self, value, log_invalid_types=True):
        self._project_log_invalid_types = log_invalid_types
        self.child_obj.update_studio_value(value, log_invalid_types)

    def _discard_changes(self, *args, **kwargs):
        self.child_obj.discard_changes(*args, **kwargs)

    def _add_to_studio_default(self, *args, **kwargs):
        self.child_obj.add_to_studio_default(*args, **kwargs)

    def _remove_from_studio_default(self, *args, **kwargs):
        self.child_obj.remove_from_studio_default(*args, **kwargs)

    def _add_to_project_override(self, *args, **kwargs):
        self.child_obj.add_to_project_override(*args, **kwargs)

    def _remove_from_project_override(self, *args, **kwargs):
        self.child_obj.remove_from_project_override(*args, **kwargs)

    def reset_callbacks(self):
        super(PathEntity, self).reset_callbacks()
        self.child_obj.reset_callbacks()


class ListStrictEntity(ItemEntity):
    schema_types = ["list-strict"]
    _key_regex = re.compile(r"[0-9]+")

    def __getitem__(self, idx):
        if not isinstance(idx, int):
            idx = int(idx)
        return self.children[idx]

    def __setitem__(self, idx, value):
        if not isinstance(idx, int):
            idx = int(idx)
        self.children[idx].set(value)

    def get(self, idx, default=None):
        if not isinstance(idx, int):
            idx = int(idx)

        if idx < len(self.children):
            return self.children[idx]
        return default

    def has_child_with_key(self, key):
        if (
            key
            and isinstance(key, six.string_types)
            and self._key_regex.match(key)
        ):
            key = int(key)

        if not isinstance(key, int):
            return False

        return 0 <= key < len(self.children)

    def _item_initialization(self):
        self.valid_value_types = (list, )
        self.require_key = True

        self.initial_value = None

        self._ignore_child_changes = False

        # Child items
        self.object_types = self.schema_data["object_types"]

        self.children = []
        for children_schema in self.object_types:
            child_obj = self.create_schema_object(children_schema, self, True)
            self.children.append(child_obj)

        # GUI attribute
        self.is_horizontal = self.schema_data.get("horizontal", True)
        if self.group_item is None and not self.is_group:
            self.is_group = True

    def schema_validations(self):
        # List entity must have file parent.
        if (
            not self.is_dynamic_schema_node
            and not self.is_in_dynamic_schema_node
            and not self.is_file
            and self.file_item is None
        ):
            raise EntitySchemaError(
                self, "Missing file entity in hierarchy."
            )

        super(ListStrictEntity, self).schema_validations()

    def collect_static_entities_by_path(self):
        output = {}
        if self.is_dynamic_item or self.is_in_dynamic_item:
            return output

        output[self.path] = self
        for child_obj in self.children:
            result = child_obj.collect_static_entities_by_path()
            if result:
                output.update(result)
        return output

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
        new_value = self.convert_to_valid_type(value)
        for idx, item in enumerate(new_value):
            self.children[idx].set(item)

    def collect_dynamic_schema_entities(self, collector):
        if self.is_dynamic_schema_node:
            collector.add_entity(self)

    def settings_value(self):
        if self._override_state is OverrideState.NOT_DEFINED:
            return NOT_SET

        if (
            self.is_group
            and self._override_state is not OverrideState.DEFAULTS
        ):
            if self._override_state is OverrideState.STUDIO:
                if not self.has_studio_override:
                    return NOT_SET
            elif self._override_state is OverrideState.PROJECT:
                if not self.has_project_override:
                    return NOT_SET

        output = []
        for child_obj in self.children:
            output.append(child_obj.settings_value())
        return output

    def on_change(self):
        for callback in self.on_change_callbacks:
            callback()
        self.parent.on_child_change(self)

    def on_child_change(self, _child_obj):
        if self._ignore_child_changes:
            return

        if self._override_state is OverrideState.STUDIO:
            self._has_studio_override = self._child_has_studio_override
        elif self._override_state is OverrideState.PROJECT:
            self._has_project_override = self._child_has_project_override

        self.on_change()

    @property
    def has_unsaved_changes(self):
        if self._override_state is OverrideState.NOT_DEFINED:
            return False

        if self._override_state is OverrideState.DEFAULTS:
            if not self.has_default_value:
                return True

        elif self._override_state is OverrideState.STUDIO:
            if self.had_studio_override != self._has_studio_override:
                return True

            if not self._has_studio_override and not self.has_default_value:
                return True

        elif self._override_state is OverrideState.PROJECT:
            if self.had_project_override != self._has_project_override:
                return True

            if (
                not self._has_project_override
                and not self._has_studio_override
                and not self.has_default_value
            ):
                return True

        if self._child_has_unsaved_changes:
            return True

        if self.settings_value() != self.initial_value:
            return True
        return False

    @property
    def has_studio_override(self):
        return self._has_studio_override or self._child_has_studio_override

    @property
    def has_project_override(self):
        return self._has_project_override or self._child_has_project_override

    @property
    def _child_has_unsaved_changes(self):
        for child_obj in self.children:
            if child_obj.has_unsaved_changes:
                return True
        return False

    @property
    def _child_has_studio_override(self):
        for child_obj in self.children:
            if child_obj.has_studio_override:
                return True
        return False

    @property
    def _child_has_project_override(self):
        for child_obj in self.children:
            if child_obj.has_project_override:
                return True
        return False

    def set_override_state(self, state, ignore_missing_defaults):
        # Trigger override state change of root if is not same
        if self.root_item.override_state is not state:
            self.root_item.set_override_state(state)
            return

        self._override_state = state
        self._ignore_missing_defaults = ignore_missing_defaults
        # Ignore if is dynamic item and use default in that case
        if not self.is_dynamic_item and not self.is_in_dynamic_item:
            if state > OverrideState.DEFAULTS:
                if (
                    not self.has_default_value
                    and not ignore_missing_defaults
                ):
                    raise DefaultsNotDefined(self)

            elif state > OverrideState.STUDIO:
                if (
                    not self.had_studio_override
                    and not ignore_missing_defaults
                ):
                    raise StudioDefaultsNotDefined(self)

        for child_entity in self.children:
            child_entity.set_override_state(state, ignore_missing_defaults)

        self.initial_value = self.settings_value()

    def _discard_changes(self, on_change_trigger):
        for child_obj in self.children:
            child_obj.discard_changes(on_change_trigger)

    def _add_to_studio_default(self, _on_change_trigger):
        self._has_studio_override = True
        self.on_change()

    def _remove_from_studio_default(self, on_change_trigger):
        self._ignore_child_changes = True

        for child_obj in self.children:
            child_obj.remove_from_studio_default(on_change_trigger)

        self._ignore_child_changes = False

        self._has_studio_override = False

    def _add_to_project_override(self, _on_change_trigger):
        self._has_project_override = True
        self.on_change()

    def _remove_from_project_override(self, on_change_trigger):
        self._ignore_child_changes = True

        for child_obj in self.children:
            child_obj.remove_from_project_override(on_change_trigger)

        self._ignore_child_changes = False

        self._has_project_override = False

    def _check_update_value(self, value, value_type, log_invalid_types=True):
        value = super(ListStrictEntity, self)._check_update_value(
            value, value_type, log_invalid_types
        )
        if value is NOT_SET:
            return value

        child_len = len(self.children)
        value_len = len(value)
        if value_len == child_len:
            return value

        if log_invalid_types:
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

    def update_default_value(self, value, log_invalid_types=True):
        self._default_log_invalid_types = log_invalid_types
        value = self._check_update_value(
            value, "default", log_invalid_types
        )
        self.has_default_value = value is not NOT_SET
        if value is NOT_SET:
            for child_obj in self.children:
                child_obj.update_default_value(value, log_invalid_types)

        else:
            for idx, item_value in enumerate(value):
                self.children[idx].update_default_value(
                    item_value, log_invalid_types
                )

    def update_studio_value(self, value, log_invalid_types=True):
        self._studio_log_invalid_types = log_invalid_types
        value = self._check_update_value(
            value, "studio override", log_invalid_types
        )
        if value is NOT_SET:
            for child_obj in self.children:
                child_obj.update_studio_value(value, log_invalid_types)

        else:
            for idx, item_value in enumerate(value):
                self.children[idx].update_studio_value(
                    item_value, log_invalid_types
                )

    def update_project_value(self, value, log_invalid_types=True):
        self._project_log_invalid_types = log_invalid_types
        value = self._check_update_value(
            value, "project override", log_invalid_types
        )
        if value is NOT_SET:
            for child_obj in self.children:
                child_obj.update_project_value(value, log_invalid_types)

        else:
            for idx, item_value in enumerate(value):
                self.children[idx].update_project_value(
                    item_value, log_invalid_types
                )

    def reset_callbacks(self):
        super(ListStrictEntity, self).reset_callbacks()
        for child_obj in self.children:
            child_obj.reset_callbacks()
