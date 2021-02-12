import copy

from .lib import (
    NOT_SET,
    OverrideState
)
from . import ItemEntity
from .exceptions import DefaultsNotDefined
from pype.settings.constants import (
    METADATA_KEYS,
    M_DYNAMIC_KEY_LABEL,
    M_ENVIRONMENT_KEY
)


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

    def pop(self, key, *args, **kwargs):
        result = self.children_by_key.pop(key, *args, **kwargs)
        self.on_change()
        return result

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

    def set(self, value):
        self._validate_value_type(value)

        prev_keys = set(self.keys())

        for _key, _value in value.items():
            self.set_value_for_key(_key, _value)
            if _key in prev_keys:
                prev_keys.remove(_key)

        for key in prev_keys:
            self.pop(key)

    def set_value_for_key(self, key, value):
        # TODO Check for value type if is Settings entity?
        child_obj = self.children_by_key.get(key)
        if not child_obj:
            child_obj = self.add_key(key)

        child_obj.set(value)

    def change_key(self, old_key, new_key):
        if new_key == old_key:
            return
        self.children_by_key[new_key] = self.children_by_key.pop(old_key)
        self.on_change()

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
    def _add_key(self, key):
        if key in self.children_by_key:
            self.pop(key)

        if self.value_is_env_group:
            item_schema = copy.deepcopy(self.item_schema)
            item_schema["env_group_key"] = key
        else:
            item_schema = self.item_schema

        new_child = self.create_schema_object(item_schema, self, True)
        self.children_by_key[key] = new_child
        return new_child

    def add_key(self, key):
        new_child = self._add_key(key)
        new_child.set_override_state(self._override_state)
        self.on_change()
        return new_child

    def _item_initalization(self):
        self._default_metadata = {}
        self._studio_override_metadata = {}
        self._project_override_metadata = {}

        self.initial_value = None

        self._ignore_child_changes = False

        self.valid_value_types = (dict, )
        self.value_on_not_set = {}

        self.children_by_key = {}
        self.children_label_by_id = {}

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

        for child_obj in self.children_by_key.values():
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

    def _metadata_for_current_state(self):
        if (
            self._override_state is OverrideState.PROJECT
            and self._project_override_value is not NOT_SET
        ):
            return self._project_override_metadata

        if (
            self._override_state >= OverrideState.STUDIO
            and self._studio_override_value is not NOT_SET
        ):
            return self._studio_override_metadata

        return self._default_metadata

    def set_override_state(self, state):
        # Trigger override state change of root if is not same
        if self.root_item.override_state is not state:
            self.root_item.set_override_state(state)
            return

        # TODO change metadata
        self._override_state = state
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
            value = self._project_override_value
            metadata = self._project_override_metadata

        elif self.had_studio_override:
            value = self._studio_override_value
            metadata = self._studio_override_metadata

        else:
            using_overrides = False
            value = self._default_value
            metadata = self._default_metadata

        if value is NOT_SET:
            value = self.value_on_not_set

        new_value = copy.deepcopy(value)

        # Simulate `clear` method without triggering value change
        for key in tuple(self.children_by_key.keys()):
            child_obj = self.children_by_key.pop(key)

        # Create new children
        children_label_by_id = {}
        metadata_labels = metadata.get(M_DYNAMIC_KEY_LABEL) or {}
        for _key, _value in new_value.items():
            child_obj = self._add_key(_key)
            child_obj.update_default_value(_value)
            if using_overrides:
                if state is OverrideState.STUDIO:
                    child_obj.update_studio_values(_value)
                else:
                    child_obj.update_project_values(_value)

            label = metadata_labels.get(_key)
            if label:
                children_label_by_id[child_obj.id] = label
            child_obj.set_override_state(state)

        self.children_label_by_id = children_label_by_id

        self.initial_value = self.settings_value()

    def children_key_by_id(self):
        return {
            child_entity.id: key
            for key, child_entity in self.children_by_key.items()
        }

    @property
    def value(self):
        output = {}
        for key, child_entity in self.children_by_key.items():
            output[key] = child_entity.value
        return output

    @property
    def metadata(self):
        output = {}
        if not self.children_label_by_id:
            return output

        children_key_by_id = self.children_key_by_id()
        label_metadata = {}
        for child_id, label in self.children_label_by_id.items():
            key = children_key_by_id[child_id]
            label_metadata[key] = label

        output[M_DYNAMIC_KEY_LABEL] = label_metadata

        return output

    @property
    def has_unsaved_changes(self):
        if (
            self._override_state is OverrideState.PROJECT
            and self._has_project_override != self.had_project_override
        ):
            return True

        elif (
            self._override_state is OverrideState.STUDIO
            and self._has_studio_override != self.had_studio_override
        ):
            return True

        if self._child_has_unsaved_changes:
            return True

        if self.metadata != self._metadata_for_current_state():
            return True

        if self.settings_value() != self.initial_value:
            return True

        return False

    @property
    def _child_has_unsaved_changes(self):
        for child_obj in self.children_by_key.values():
            if child_obj.has_unsaved_changes:
                return True
        return False

    @property
    def has_studio_override(self):
        return self._has_studio_override or self._child_has_studio_override

    @property
    def _child_has_studio_override(self):
        if self._override_state >= OverrideState.STUDIO:
            for child_obj in self.children_by_key.values():
                if child_obj.has_studio_override:
                    return True
        return False

    @property
    def has_project_override(self):
        return self._has_project_override or self._child_has_project_override

    @property
    def _child_has_project_override(self):
        if self._override_state >= OverrideState.PROJECT:
            for child_obj in self.children_by_key.values():
                if child_obj.has_project_override:
                    return True
        return False

    def settings_value(self):
        if self._override_state is OverrideState.NOT_DEFINED:
            return NOT_SET

        if self.is_group:
            if self._override_state is OverrideState.STUDIO:
                if not self._has_studio_override:
                    return NOT_SET

            elif self._override_state is OverrideState.PROJECT:
                if not self._has_project_override:
                    return NOT_SET

        output = {}
        for key, child_entity in self.children_by_key.items():
            child_value = child_entity.settings_value()
            if self.value_is_env_group:
                if key not in child_value[M_ENVIRONMENT_KEY]:
                    _metadata = child_value[M_ENVIRONMENT_KEY]
                    _m_keykey = tuple(_metadata.keys())[0]
                    env_keys = child_value[M_ENVIRONMENT_KEY].pop(_m_keykey)
                    child_value[M_ENVIRONMENT_KEY][key] = env_keys
            output[key] = child_value
        output.update(self.metadata)
        return output

    def _prepare_value(self, value):
        metadata = {}
        if isinstance(value, dict):
            for key in METADATA_KEYS:
                if key in value:
                    metadata[key] = value.pop(key)
        return value, metadata

    def update_default_value(self, value):
        value = self._check_update_value(value, "default")
        self.has_default_value = value is not NOT_SET
        value, metadata = self._prepare_value(value)
        self._default_value = value
        self._default_metadata = metadata

    def update_studio_values(self, value):
        value = self._check_update_value(value, "studio override")
        value, metadata = self._prepare_value(value)
        self._studio_override_value = value
        self._studio_override_metadata = metadata
        self.had_studio_override = value is not NOT_SET

    def update_project_values(self, value):
        value = self._check_update_value(value, "project override")
        value, metadata = self._prepare_value(value)
        self._project_override_value = value
        self._project_override_metadata = metadata
        self.had_project_override = value is not NOT_SET

    def _discard_changes(self, on_change_trigger):
        self.set_override_state(self._override_state)
        on_change_trigger.append(self.on_change)

    def add_to_studio_default(self):
        if self._override_state is not OverrideState.STUDIO:
            return
        self._has_studio_override = True
        self.on_change()

    def _remove_from_studio_default(self, on_change_trigger):
        value = self._default_value
        if value is NOT_SET:
            value = self.value_on_not_set

        new_value = copy.deepcopy(value)
        self._ignore_child_changes = True

        # Simulate `clear` method without triggering value change
        for key in tuple(self.children_by_key.keys()):
            child_obj = self.children_by_key.pop(key)

        # Create new children
        for _key, _value in new_value.items():
            child_obj = self.add_key(_key)
            child_obj.update_default_value(_value)
            child_obj.set_override_state(self._override_state)

        self._ignore_child_changes = False

        self._has_studio_override = False

        on_change_trigger.append(self.on_change)

    def add_to_project_override(self):
        if self._override_state is not OverrideState.PROJECT:
            return
        self._has_project_override = True
        self.on_change()

    def _remove_from_project_override(self, on_change_trigger):
        if self._override_state is not OverrideState.PROJECT:
            return

        if not self.has_project_override:
            return

        using_overrides = False
        if self._has_studio_override:
            value = self._studio_override_value
            using_overrides = True
        elif self.has_default_value:
            value = self._default_value
        else:
            value = self.value_on_not_set

        new_value = copy.deepcopy(value)

        self._ignore_child_changes = True

        # Simulate `clear` method without triggering value change
        for key in tuple(self.children_by_key.keys()):
            child_obj = self.children_by_key.pop(key)

        # Create new children
        for _key, _value in new_value.items():
            child_obj = self.add_key(_key)
            child_obj.update_default_value(_value)
            if using_overrides:
                child_obj.update_studio_value(_value)
            child_obj.set_override_state(self._override_state)

        self._ignore_child_changes = False

        self._has_project_override = False

        on_change_trigger.append(self.on_change)

    def reset_callbacks(self):
        super(DictMutableKeysEntity, self).reset_callbacks()
        for child_entity in self.children_by_key.values():
            child_entity.reset_callbacks()
