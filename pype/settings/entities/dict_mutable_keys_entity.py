import copy

from .lib import (
    NOT_SET,
    DefaultsNotDefined
)
from .constants import (
    OverrideState,
    METADATA_KEYS,
    M_DYNAMIC_KEY_LABEL,
    M_ENVIRONMENT_KEY
)
from . import ItemEntity


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

    def __contains__(self, key):
        return key in self.children_by_key

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

    def change_key(self, old_key, new_key):
        if new_key == old_key:
            return
        self.children_by_key[new_key] = self.children_by_key.pop(old_key)

    def change_child_key(self, child_entity, new_key):
        old_key = None
        for key, child in self.children_by_key.items():
            if child is child_entity:
                old_key = key
                break

        self.change_key(old_key, new_key)

    def get_child_key(self, child_entity):
        for key, child in self.children_by_key.items():
            if child is child_entity:
                return key
        return None

    def add_new_key(self, key):
        new_child = self.create_schema_object(self.item_schema, self, True)
        new_child.set_override_state(self.override_state)
        self.children.append(new_child)
        self.children_by_key[key] = new_child
        return new_child

    def item_initalization(self):
        self.default_metadata = {}
        self.studio_override_metadata = {}
        self.project_override_metadata = {}

        self.initial_value = None

        self.ignore_child_changes = False

        # current_metadata are still when schema is loaded
        self.current_metadata = {}

        self.valid_value_types = (dict, )
        self.value_on_not_set = {}

        self.children = []
        self.children_by_key = {}
        self._current_value = NOT_SET

        self.value_is_env_group = (
            self.schema_data.get("value_is_env_group") or False
        )
        self.required_keys = self.schema_data.get("required_keys") or []
        self.collapsible_key = self.schema_data.get("collapsable_key") or False
        # GUI attributes
        self.hightlight_content = (
            self.schema_data.get("highlight_content") or False
        )
        self.collapsible = self.schema_data.get("collapsable", True)
        self.collapsed = self.schema_data.get("collapsed", True)

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

        if self.value_is_env_group:
            self.item_schema["env_group_key"] = ""

        if not self.group_item:
            self.is_group = True

    def schema_validations(self):
        super(DictMutableKeysEntity, self).schema_validations()

        # TODO Ability to store labels should be defined with different key
        if self.collapsible_key and not self.file_item:
            raise ValueError((
                "{}: Modifiable dictionary with collapsible keys is not under"
                " file item so can't store metadata."
            ).format(self.path))

        for child_obj in self.children:
            child_obj.schema_validations()

    def get_child_path(self, child_obj):
        result_key = None
        for key, _child_obj in self.children_by_key.items():
            if _child_obj is child_obj:
                result_key = key
                break

        if result_key is None:
            raise ValueError("Didn't found child {}".format(child_obj))

        return "/".join([self.path, result_key])

    def set_value_for_key(self, key, value, batch=False):
        # TODO Check for value type if is Settings entity?
        child_obj = self.children_by_key.get(key)
        if not child_obj:
            child_obj = self.add_new_key(key)

        child_obj.set_value(value)

        if not batch:
            self.on_value_change()

    def on_change(self):
        for callback in self.on_change_callbacks:
            callback()
        self.parent.on_child_change(self)

    def on_child_change(self, _child_obj):
        if not self.ignore_child_changes:
            self.on_change()

    def _metadata_for_current_state(self):
        if (
            self.override_state is OverrideState.PROJECT
            and self.project_override_value is not NOT_SET
        ):
            metadata = self.project_override_metadata

        elif self.studio_override_value is not NOT_SET:
            metadata = self.studio_override_metadata
        else:
            metadata = self.default_metadata
        return metadata

    def get_metadata_from_value(self, value, previous_metadata):
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
        # TODO pop keys not in value and add new keys from value
        for _key, _value in value.items():
            self.set_value_for_key(_key, _value, True)
        self.on_value_change()

    def on_value_change(self):
        if self.override_state is OverrideState.NOT_DEFINED:
            return

        if self.override_state is OverrideState.STUDIO:
            self._has_studio_override = True

        elif self.override_state is OverrideState.PROJECT:
            self._has_project_override = True

        self.on_change()

    def set_override_state(self, state):
        # TODO change metadata
        self.override_state = state
        if not self.has_default_value and state > OverrideState.DEFAULTS:
            # Ignore if is dynamic item and use default in that case
            if not self.is_dynamic_item and not self.is_in_dynamic_item:
                raise DefaultsNotDefined(self)

        if state is OverrideState.STUDIO:
            self._has_studio_override = self.had_studio_override

        elif state is OverrideState.PROJECT:
            self._has_project_override = self.had_project_override
            self._has_studio_override = self.had_studio_override

        using_overrides = True
        if (
            state is OverrideState.PROJECT
            and self.had_project_override
        ):
            value = self.project_override_value
            metadata = self.project_override_metadata

        elif self.had_studio_override:
            value = self.studio_override_value
            metadata = self.studio_override_metadata

        else:
            using_overrides = False
            value = self.default_value
            metadata = self.default_metadata

        # TODO REQUIREMENT value must be stored to _current_value
        # - current value must not be dynamic!!!
        # - it is required to update metadata on the fly
        if value is NOT_SET:
            value = self.value_on_not_set

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
            child_obj = self.add_new_key(_key)
            child_obj.update_default_value(_value)
            if using_overrides:
                if state is OverrideState.STUDIO:
                    child_obj.update_studio_values(value)
                else:
                    child_obj.update_project_values(value)

            child_obj.set_override_state(state)

        self.initial_value = self.settings_value()

    @property
    def value(self):
        return self._current_value

    @property
    def has_unsaved_changes(self):
        if (
            self.override_state is OverrideState.PROJECT
            and self._has_project_override != self.had_project_override
        ):
            return True

        elif (
            self.override_state is OverrideState.STUDIO
            and self._has_studio_override != self.had_studio_override
        ):
            return True

        if self.child_is_modified:
            return True

        if self.settings_value() != self.initial_value:
            return True
        return False

    @property
    def child_is_modified(self):
        for child_obj in self.children:
            if child_obj.has_unsaved_changes:
                return True
        return False

    @property
    def has_studio_override(self):
        return self._has_studio_override or self.child_has_studio_override

    @property
    def child_has_studio_override(self):
        if self.override_state >= OverrideState.STUDIO:
            for child_obj in self.children:
                if child_obj.has_studio_override:
                    return True
        return False

    @property
    def has_project_override(self):
        return self._has_project_override or self.child_has_project_override

    @property
    def child_has_project_override(self):
        if self.override_state >= OverrideState.PROJECT:
            if self._has_project_override:
                return True

            for child_obj in self.children:
                if child_obj.has_project_override:
                    return True
        return False

    def settings_value(self):
        if self.override_state is OverrideState.NOT_DEFINED:
            return NOT_SET

        if self.is_group:
            if self.override_state is OverrideState.STUDIO:
                if not self._has_studio_override:
                    return NOT_SET

            elif self.override_state is OverrideState.PROJECT:
                if not self._has_project_override:
                    return NOT_SET

        output = copy.deepcopy(self._current_value)
        output.update(copy.deepcopy(self.current_metadata))
        return output

    def _prepare_value(self, value):
        metadata = {}
        if isinstance(value, dict):
            for key in METADATA_KEYS:
                if key in value:
                    metadata[key] = value.pop(key)
        return value, metadata

    def update_default_value(self, value):
        self.has_default_value = value is not NOT_SET
        value, metadata = self._prepare_value(value)
        self.default_value = value
        self.default_metadata = metadata

    def update_studio_values(self, value):
        value, metadata = self._prepare_value(value)
        self.studio_override_value = value
        self.studio_override_metadata = metadata
        self.had_studio_override = value is not NOT_SET

    def update_project_values(self, value):
        value, metadata = self._prepare_value(value)
        self.project_override_value = value
        self.project_override_metadata = metadata
        self.had_project_override = value is not NOT_SET

    def _discard_changes(self, on_change_trigger):
        self.set_override_state(self.override_state)
        on_change_trigger.append(self.on_change)

    def set_studio_default(self):
        if self.override_state is not OverrideState.STUDIO:
            return
        self._has_studio_override = True
        self.on_change()

    def reset_to_pype_default(self):
        if self.override_state is not OverrideState.STUDIO:
            return

        value = self.default_value
        metadata = self.default_metadata
        if value is NOT_SET:
            value = self.value_on_not_set

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
            child_obj = self.add_new_key(_key)
            child_obj.update_default_value(_value)
            child_obj.set_override_state(self.override_state)

        self._has_studio_override = False
        self.on_change()

    def set_as_overriden(self):
        if self.override_state is not OverrideState.PROJECT:
            return
        self._has_project_override = True
        self.on_change()

    def remove_overrides(self):
        if self.override_state is not OverrideState.PROJECT:
            return

        if not self._has_project_override:
            return

        using_overrides = False
        metadata = self.default_metadata
        if self._has_studio_override:
            value = self.studio_override_value
            metadata = self.studio_override_metadata
            using_overrides = True
        elif self.has_default_value:
            value = self.default_value
        else:
            value = self.value_on_not_set

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
            child_obj = self.add_new_key(_key)
            child_obj.update_default_value(_value)
            if using_overrides:
                child_obj.update_studio_value(_value)
            child_obj.set_override_state(self.override_state)

        self._has_project_override = False

        self.on_change()
