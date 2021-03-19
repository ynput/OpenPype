import copy
from abc import abstractmethod

from .base_entity import ItemEntity
from .lib import (
    NOT_SET,
    STRING_TYPE,
    OverrideState
)
from .exceptions import (
    DefaultsNotDefined,
    StudioDefaultsNotDefined
)

from pype.settings.constants import (
    METADATA_KEYS,
    M_ENVIRONMENT_KEY
)


class EndpointEntity(ItemEntity):
    """Entity that is a endpoint of settings value.

    In most of cases endpoint entity does not have children entities and if has
    then they are dynamic and can be removed/created. Is automatically set as
    group if any parent is not, that is because of override metadata.
    """

    def __init__(self, *args, **kwargs):
        super(EndpointEntity, self).__init__(*args, **kwargs)

        if (
            not (self.group_item or self.is_group)
            and not (self.is_dynamic_item or self.is_in_dynamic_item)
        ):
            self.is_group = True

    def schema_validations(self):
        """Validation of entity schema and schema hierarchy."""
        # Default value when even defaults are not filled must be set
        if self.value_on_not_set is NOT_SET:
            raise ValueError(
                "Attribute `value_on_not_set` is not filled. {}".format(
                    self.__class__.__name__
                )
            )

        super(EndpointEntity, self).schema_validations()

    @abstractmethod
    def _settings_value(self):
        pass

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
        self.parent.on_child_change(self)

    def update_default_value(self, value):
        value = self._check_update_value(value, "default")
        self._default_value = value
        self.has_default_value = value is not NOT_SET

    def update_studio_value(self, value):
        value = self._check_update_value(value, "studio override")
        self._studio_override_value = value
        self.had_studio_override = bool(value is not NOT_SET)

    def update_project_value(self, value):
        value = self._check_update_value(value, "project override")
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

    def get_child_path(self, child_obj):
        raise TypeError("{} can't have children".format(
            self.__class__.__name__
        ))

    def schema_validations(self):
        # Input entity must have file parent.
        if not self.file_item:
            raise ValueError(
                "{}: Missing parent file entity.".format(self.path)
            )

        super(InputEntity, self).schema_validations()

    @property
    def value(self):
        """Entity's value without metadata."""
        return self._current_value

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

    def set_override_state(self, state):
        # Trigger override state change of root if is not same
        if self.root_item.override_state is not state:
            self.root_item.set_override_state(state)
            return

        self._override_state = state
        # Ignore if is dynamic item and use default in that case
        if not self.is_dynamic_item and not self.is_in_dynamic_item:
            if state > OverrideState.DEFAULTS:
                if not self.has_default_value:
                    raise DefaultsNotDefined(self)

            elif state > OverrideState.STUDIO:
                if not self.had_studio_override:
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
        if self._override_state is not OverrideState.PROJECT:
            return

        if not self._has_project_override:
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

    def _item_initalization(self):
        self.minimum = self.schema_data.get("minimum", -99999)
        self.maximum = self.schema_data.get("maximum", 99999)
        self.decimal = self.schema_data.get("decimal", 0)

        if self.decimal:
            valid_value_types = (float, )
        else:
            valid_value_types = (int, )
        self.valid_value_types = valid_value_types
        self.value_on_not_set = 0

    def _convert_to_valid_type(self, value):
        if self.decimal:
            if isinstance(value, int):
                return float(value)
        else:
            if isinstance(value, float):
                new_value = int(value)
                if new_value != value:
                    self.log.info("Converted float {} to int {}".format(
                        value, new_value
                    ))
                return new_value
        return NOT_SET


class BoolEntity(InputEntity):
    schema_types = ["boolean"]

    def _item_initalization(self):
        self.valid_value_types = (bool, )
        self.value_on_not_set = True


class TextEntity(InputEntity):
    schema_types = ["text"]

    def _item_initalization(self):
        self.valid_value_types = (STRING_TYPE, )
        self.value_on_not_set = ""

        # GUI attributes
        self.multiline = self.schema_data.get("multiline", False)
        self.placeholder_text = self.schema_data.get("placeholder")


class PathInput(InputEntity):
    schema_types = ["path-input"]

    def _item_initalization(self):
        self.with_arguments = self.schema_data.get("with_arguments", False)
        if self.with_arguments:
            self.valid_value_types = (list, )
            self.value_on_not_set = ["", ""]
        else:
            self.valid_value_types = (STRING_TYPE, )
            self.value_on_not_set = ""


class RawJsonEntity(InputEntity):
    schema_types = ["raw-json"]

    def _item_initalization(self):
        # Schema must define if valid value is dict or list
        self.valid_value_types = (list, dict)
        self.value_on_not_set = {}

        self.default_metadata = {}
        self.studio_override_metadata = {}
        self.project_override_metadata = {}

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
        output = {}
        if isinstance(self._current_value, dict) and self.is_env_group:
            output[M_ENVIRONMENT_KEY] = {
                self.env_group_key: list(self._current_value.keys())
            }

        return output

    @property
    def has_unsaved_changes(self):
        result = super(RawJsonEntity, self).has_unsaved_changes
        if not result:
            result = self.metadata != self._metadata_for_current_state()
        return result

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
        if self.is_env_group and isinstance(value, dict):
            value.update(self.metadata)
        return value

    def _prepare_value(self, value):
        metadata = {}
        if isinstance(value, dict):
            value = copy.deepcopy(value)
            for key in METADATA_KEYS:
                if key in value:
                    metadata[key] = value.pop(key)
        return value, metadata

    def update_default_value(self, value):
        value = self._check_update_value(value, "default")
        self.has_default_value = value is not NOT_SET
        value, metadata = self._prepare_value(value)
        self._default_value = value
        self.default_metadata = metadata

    def update_studio_value(self, value):
        value = self._check_update_value(value, "studio override")
        self.had_studio_override = value is not NOT_SET
        value, metadata = self._prepare_value(value)
        self._studio_override_value = value
        self.studio_override_metadata = metadata

    def update_project_value(self, value):
        value = self._check_update_value(value, "project override")
        self.had_project_override = value is not NOT_SET
        value, metadata = self._prepare_value(value)
        self._project_override_value = value
        self.project_override_metadata = metadata
