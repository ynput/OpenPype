import re
import copy
import json
from abc import abstractmethod

from .base_entity import ItemEntity
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

from openpype.settings.constants import METADATA_KEYS


class EndpointEntity(ItemEntity):
    """Entity that is a endpoint of settings value.

    In most of cases endpoint entity does not have children entities and if has
    then they are dynamic and can be removed/created. Is automatically set as
    group if any parent is not, that is because of override metadata.
    """

    def __init__(self, *args, **kwargs):
        super(EndpointEntity, self).__init__(*args, **kwargs)

        if (
            not (self.group_item is not None or self.is_group)
            and not (self.is_dynamic_item or self.is_in_dynamic_item)
        ):
            self.is_group = True

    def schema_validations(self):
        """Validation of entity schema and schema hierarchy."""
        # Default value when even defaults are not filled must be set
        if self.value_on_not_set is NOT_SET:
            reason = "Attribute `value_on_not_set` is not filled. {}".format(
                self.__class__.__name__
            )
            raise EntitySchemaError(self, reason)

        super(EndpointEntity, self).schema_validations()

    def collect_dynamic_schema_entities(self, collector):
        if self.is_dynamic_schema_node:
            collector.add_entity(self)

    @abstractmethod
    def _settings_value(self):
        pass

    def collect_static_entities_by_path(self):
        if self.is_dynamic_item or self.is_in_dynamic_item:
            return {}
        return {self.path: self}

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
        return self._settings_value()

    def on_change(self):
        for callback in self.on_change_callbacks:
            callback()

        if self.require_restart_on_change:
            if self.require_restart:
                self.root_item.add_item_require_restart(self)
            else:
                self.root_item.remove_item_require_restart(self)
        self.parent.on_child_change(self)

    @property
    def require_restart(self):
        return self.has_unsaved_changes

    def update_default_value(self, value, log_invalid_types=True):
        self._default_log_invalid_types = log_invalid_types
        value = self._check_update_value(
            value, "default", log_invalid_types
        )
        self._default_value = value
        self.has_default_value = value is not NOT_SET

    def update_studio_value(self, value, log_invalid_types=True):
        self._studio_log_invalid_types = log_invalid_types
        value = self._check_update_value(
            value, "studio override", log_invalid_types
        )
        self._studio_override_value = value
        self.had_studio_override = bool(value is not NOT_SET)

    def update_project_value(self, value, log_invalid_types=True):
        self._project_log_invalid_types = log_invalid_types
        value = self._check_update_value(
            value, "project override", log_invalid_types
        )
        self._project_override_value = value
        self.had_project_override = bool(value is not NOT_SET)


class InputEntity(EndpointEntity):
    """Endpoint entity without children."""
    def __init__(self, *args, **kwargs):
        super(InputEntity, self).__init__(*args, **kwargs)
        self._value_is_modified = False
        self._current_value = NOT_SET

    def __eq__(self, other):
        if isinstance(other, ItemEntity):
            return self.value == other.value
        return self.value == other

    def has_child_with_key(self, key):
        return False

    def get_child_path(self, child_obj):
        raise TypeError("{} can't have children".format(
            self.__class__.__name__
        ))

    def schema_validations(self):
        # Input entity must have file parent.
        if (
            not self.is_dynamic_schema_node
            and not self.is_in_dynamic_schema_node
            and self.file_item is None
        ):
            raise EntitySchemaError(self, "Missing parent file entity.")

        super(InputEntity, self).schema_validations()

    @property
    def value(self):
        """Entity's value without metadata."""
        return self._current_value

    @property
    def require_restart(self):
        return self._value_is_modified

    def _settings_value(self):
        return copy.deepcopy(self.value)

    def set(self, value):
        """Change value."""
        self._current_value = self.convert_to_valid_type(value)
        self._on_value_change()

    def _on_value_change(self):
        # Change has_project_override attr value
        if self._override_state is OverrideState.PROJECT:
            self._has_project_override = True

        elif self._override_state is OverrideState.STUDIO:
            self._has_studio_override = True

        self.on_change()

    def on_change(self):
        """Callback triggered on change.

        There are cases when this method may be called from other entity.
        """
        value_is_modified = None
        if self._override_state is OverrideState.PROJECT:
            # Only value change
            if (
                self._has_project_override
                and self._project_override_value is not NOT_SET
            ):
                value_is_modified = (
                    self._current_value != self._project_override_value
                )

        if (
            self._override_state is OverrideState.STUDIO
            or value_is_modified is None
        ):
            if (
                self._has_studio_override
                and self._studio_override_value is not NOT_SET
            ):
                value_is_modified = (
                    self._current_value != self._studio_override_value
                )

        if value_is_modified is None:
            value_is_modified = self._current_value != self._default_value

        self._value_is_modified = value_is_modified

        super(InputEntity, self).on_change()

    def on_child_change(self, child_obj):
        raise TypeError("Input entities do not contain children.")

    @property
    def has_unsaved_changes(self):
        if self._override_state is OverrideState.NOT_DEFINED:
            return False

        if self._value_is_modified:
            return True

        # These may be stored on value change
        if self._override_state is OverrideState.DEFAULTS:
            if not self.has_default_value:
                return True

        elif self._override_state is OverrideState.STUDIO:
            if self._has_studio_override != self.had_studio_override:
                return True

            if not self._has_studio_override and not self.has_default_value:
                return True

        elif self._override_state is OverrideState.PROJECT:
            if self._has_project_override != self.had_project_override:
                return True

            if (
                not self._has_project_override
                and not self._has_studio_override
                and not self.has_default_value
            ):
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

        if state is OverrideState.STUDIO:
            self._has_studio_override = (
                self._studio_override_value is not NOT_SET
            )

        elif state is OverrideState.PROJECT:
            self._has_project_override = (
                self._project_override_value is not NOT_SET
            )
            self._has_studio_override = self.had_studio_override

        value = NOT_SET
        if state is OverrideState.PROJECT:
            value = self._project_override_value

        if value is NOT_SET and state >= OverrideState.STUDIO:
            value = self._studio_override_value

        if value is NOT_SET and state >= OverrideState.DEFAULTS:
            value = self._default_value

        if value is NOT_SET:
            value = self.value_on_not_set
            self.has_default_value = False
        else:
            self.has_default_value = True
        self._value_is_modified = False

        self._current_value = copy.deepcopy(value)

    def _discard_changes(self, on_change_trigger=None):
        if not self._can_discard_changes:
            return

        self._value_is_modified = False
        if self._override_state >= OverrideState.PROJECT:
            self._has_project_override = self.had_project_override
            if self.had_project_override:
                self._current_value = copy.deepcopy(
                    self._project_override_value
                )
                on_change_trigger.append(self.on_change)
                return

        if self._override_state >= OverrideState.STUDIO:
            self._has_studio_override = self.had_studio_override
            if self.had_studio_override:
                self._current_value = copy.deepcopy(
                    self._studio_override_value
                )
                on_change_trigger.append(self.on_change)
                return

        if self._override_state >= OverrideState.DEFAULTS:
            if self.has_default_value:
                value = self._default_value
            else:
                value = self.value_on_not_set
            self._current_value = copy.deepcopy(value)
            on_change_trigger.append(self.on_change)
            return

        raise NotImplementedError("BUG: Unexcpected part of code.")

    def _add_to_studio_default(self, _on_change_trigger):
        self._has_studio_override = True
        self.on_change()

    def _remove_from_studio_default(self, on_change_trigger):
        if not self._can_remove_from_studio_default:
            return

        value = self._default_value
        if value is NOT_SET:
            value = self.value_on_not_set
        self._current_value = copy.deepcopy(value)

        self._has_studio_override = False
        self._value_is_modified = False

        on_change_trigger.append(self.on_change)

    def _add_to_project_override(self, _on_change_trigger):
        self._has_project_override = True
        self.on_change()

    def _remove_from_project_override(self, on_change_trigger):
        if not self._can_remove_from_project_override:
            return

        self._has_project_override = False
        if self._has_studio_override:
            current_value = self._studio_override_value
        elif self.has_default_value:
            current_value = self._default_value
        else:
            current_value = self.value_on_not_set

        self._current_value = copy.deepcopy(current_value)
        on_change_trigger.append(self.on_change)


class NumberEntity(InputEntity):
    schema_types = ["number"]
    float_number_regex = re.compile(r"^\d+\.\d+$")
    int_number_regex = re.compile(r"^\d+$")

    def _item_initialization(self):
        self.minimum = self.schema_data.get("minimum", -99999)
        self.maximum = self.schema_data.get("maximum", 99999)
        self.decimal = self.schema_data.get("decimal", 0)

        value_on_not_set = self.schema_data.get("default", 0)
        if self.decimal:
            valid_value_types = (float, )
            value_on_not_set = float(value_on_not_set)
        else:
            valid_value_types = (int, )
            value_on_not_set = int(value_on_not_set)
        self.valid_value_types = valid_value_types
        self.value_on_not_set = value_on_not_set

        # UI specific attributes
        self.show_slider = self.schema_data.get("show_slider", False)
        steps = self.schema_data.get("steps", None)
        # Make sure that steps are not set to `0`
        if steps == 0:
            steps = None
        self.steps = steps

    def _convert_to_valid_type(self, value):
        if isinstance(value, str):
            new_value = None
            if self.float_number_regex.match(value):
                new_value = float(value)
            elif self.int_number_regex.match(value):
                new_value = int(value)

            if new_value is not None:
                self.log.info("{} - Converted str {} to {} {}".format(
                    self.path, value, type(new_value).__name__, new_value
                ))
                value = new_value

        if self.decimal:
            if isinstance(value, float):
                return value
            if isinstance(value, int):
                return float(value)
        else:
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                new_value = int(value)
                if new_value != value:
                    self.log.info("{} - Converted float {} to int {}".format(
                        self.path, value, new_value
                    ))
                return new_value
        return NOT_SET


class BoolEntity(InputEntity):
    schema_types = ["boolean"]

    def _item_initialization(self):
        self.valid_value_types = (bool, )
        value_on_not_set = self.convert_to_valid_type(
            self.schema_data.get("default", True)
        )
        self.value_on_not_set = value_on_not_set


class TextEntity(InputEntity):
    schema_types = ["text"]

    def _item_initialization(self):
        self.valid_value_types = (STRING_TYPE, )
        self.value_on_not_set = ""

        # GUI attributes
        self.multiline = self.schema_data.get("multiline", False)
        self.placeholder_text = self.schema_data.get("placeholder")
        self.value_hints = self.schema_data.get("value_hints") or []

    def schema_validations(self):
        if self.multiline and self.value_hints:
            reason = (
                "TextEntity entity can't use value hints"
                " for multiline input (yet)."
            )
            raise EntitySchemaError(self, reason)
        super(TextEntity, self).schema_validations()

    def _convert_to_valid_type(self, value):
        # Allow numbers converted to string
        if isinstance(value, (int, float)):
            return str(value)
        return NOT_SET


class PathInput(InputEntity):
    schema_types = ["path-input"]

    def _item_initialization(self):
        self.valid_value_types = (STRING_TYPE, )
        self.value_on_not_set = ""

        # GUI attributes
        self.placeholder_text = self.schema_data.get("placeholder")

    def set(self, value):
        # Strip value
        super(PathInput, self).set(value.strip())

    def set_override_state(self, state, ignore_missing_defaults):
        super(PathInput, self).set_override_state(
            state, ignore_missing_defaults
        )
        # Strip current value
        self._current_value = self._current_value.strip()


class RawJsonEntity(InputEntity):
    schema_types = ["raw-json"]

    def _item_initialization(self):
        # Schema must define if valid value is dict or list
        store_as_string = self.schema_data.get("store_as_string", False)
        is_list = self.schema_data.get("is_list", False)
        if is_list:
            valid_value_types = (list, )
            value_on_not_set = []
        else:
            valid_value_types = (dict, )
            value_on_not_set = {}

        self.store_as_string = store_as_string

        self._is_list = is_list
        self.valid_value_types = valid_value_types
        self.value_on_not_set = value_on_not_set

        self.default_metadata = {}
        self.studio_override_metadata = {}
        self.project_override_metadata = {}

    @property
    def is_list(self):
        return self._is_list

    @property
    def is_dict(self):
        return not self._is_list

    def set(self, value):
        new_value = self.convert_to_valid_type(value)

        if isinstance(new_value, dict):
            for key in METADATA_KEYS:
                if key in new_value:
                    new_value.pop(key)
        self._current_value = new_value
        self._on_value_change()

    @property
    def metadata(self):
        return {}

    @property
    def has_unsaved_changes(self):
        result = super(RawJsonEntity, self).has_unsaved_changes
        if not result:
            result = self.metadata != self._metadata_for_current_state()
        return result

    def _convert_to_valid_type(self, value):
        if isinstance(value, STRING_TYPE):
            try:
                return json.loads(value)
            except Exception:
                pass
        return super(RawJsonEntity, self)._convert_to_valid_type(value)

    def _metadata_for_current_state(self):
        if (
            self._override_state is OverrideState.PROJECT
            and self._project_override_value is not NOT_SET
        ):
            return self.project_override_metadata

        if (
            self._override_state >= OverrideState.STUDIO
            and self._studio_override_value is not NOT_SET
        ):
            return self.studio_override_metadata

        return self.default_metadata

    def _settings_value(self):
        value = super(RawJsonEntity, self)._settings_value()
        if self.store_as_string:
            return json.dumps(value)
        return value

    def _prepare_value(self, value):
        metadata = {}
        if isinstance(value, dict):
            value = copy.deepcopy(value)
            for key in METADATA_KEYS:
                if key in value:
                    metadata[key] = value.pop(key)
        return value, metadata

    def update_default_value(self, value, log_invalid_types=True):
        value = self._check_update_value(value, "default", log_invalid_types)
        self.has_default_value = value is not NOT_SET
        value, metadata = self._prepare_value(value)
        self._default_value = value
        self.default_metadata = metadata

    def update_studio_value(self, value, log_invalid_types=True):
        value = self._check_update_value(
            value, "studio override", log_invalid_types
        )
        self.had_studio_override = value is not NOT_SET
        value, metadata = self._prepare_value(value)
        self._studio_override_value = value
        self.studio_override_metadata = metadata

    def update_project_value(self, value, log_invalid_types=True):
        value = self._check_update_value(
            value, "project override", log_invalid_types
        )
        self.had_project_override = value is not NOT_SET
        value, metadata = self._prepare_value(value)
        self._project_override_value = value
        self.project_override_metadata = metadata
