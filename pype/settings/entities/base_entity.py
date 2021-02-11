from uuid import uuid4
from abc import ABCMeta, abstractmethod, abstractproperty

import six

from .lib import (
    NOT_SET,
    OverrideState
)

from .exceptions import (
    InvalidValueType,
    SchemeGroupHierarchyBug
)

from pype.lib import PypeLogger


@six.add_metaclass(ABCMeta)
class BaseEntity:
    """Partially abstract class for Setting's item type workflow."""

    def __init__(self, schema_data, parent):
        self.schema_data = schema_data
        self.parent = parent

        # Entity id
        self._id = uuid4()

    def __hash__(self):
        return self.id

    @property
    def id(self):
        return self._id

    @abstractproperty
    def gui_type(self):
        pass

    @abstractmethod
    def schema_validations(self):
        pass


class GUIEntity(BaseEntity):
    gui_type = True

    schema_types = ["divider", "splitter", "label"]

    def __getitem__(self, key):
        return self.schema_data[key]

    def schema_validations(self):
        """TODO validate GUI schemas."""
        pass


class BaseItemEntity(BaseEntity):
    gui_type = False

    def __init__(self, schema_data, parent, is_dynamic_item=False):
        super(BaseItemEntity, self).__init__(schema_data, parent)

        # Log object created on demand with `log` attribute
        self._log = None

        # Item path attribute (may be filled or be dynamic)
        self._path = None

        # These should be set on initialization and not change then
        self.valid_value_types = getattr(self, "valid_value_types", NOT_SET)
        self.value_on_not_set = getattr(self, "value_on_not_set", NOT_SET)

        # Entity represents group entity
        #   - all children entities will be saved on modification of overrides
        self.is_group = False
        # Entity's value will be stored into file with name of it's key
        self.is_file = False
        # Reference to parent entity which has `is_group` == True
        #   - stays as None if none of parents is group
        self.group_item = None
        # Reference to parent entity which has `is_file` == True
        self.file_item = None
        # Reference to `RootEntity`
        self.root_item = None

        # Entity is dynamically created (in list or dict with mutable keys)
        #   - can be also dynamically removed
        self.is_dynamic_item = is_dynamic_item
        # Entity is in hierarchy of dynamically created entity
        self.is_in_dynamic_item = False

        # Entity will save metadata about environments
        #   - this is current possible only for RawJsonEnity
        self.is_env_group = False
        # Key of environment group key must be unique across system settings
        self.env_group_key = None

        # Roles of an entity
        self.roles = None

        # Key must be specified in schema data otherwise won't work as expected
        self.require_key = True

        # Key and label of an entity
        self.key = None
        self.label = None

        # These attributes may change values during existence of an object
        # Values
        self.default_value = NOT_SET
        self.studio_override_value = NOT_SET
        self.project_override_value = NOT_SET

        # Default input attributes
        self.has_default_value = False

        self._has_studio_override = False
        self.had_studio_override = False

        self._has_project_override = False
        self.had_project_override = False

        self.value_is_modified = False

        self.override_state = OverrideState.NOT_DEFINED

        self.on_change_callbacks = []

        roles = schema_data.get("roles")
        if roles is None and parent:
            roles = parent.roles
        elif not isinstance(roles, list):
            roles = [roles]
        self.roles = roles

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
    def set_override_state(self, state):
        pass

    @abstractmethod
    def on_change(self):
        pass

    @abstractmethod
    def on_child_change(self, child_obj):
        pass

    @abstractmethod
    def set(self, value):
        pass

    def is_value_valid_type(self, value):
        value_type = type(value)
        for valid_type in self.valid_value_types:
            if value_type is valid_type:
                return True
        return False

    def check_update_value(self, value, value_type):
        if value is NOT_SET:
            return value

        if self.is_value_valid_type(value):
            return value

        self.log.warning(
            (
                "{} Got invalid value type for {} values."
                " Expected types: {} | Got Type: {} | Value: \"{}\""
            ).format(
                self.path, value_type,
                self.valid_value_types, type(value), str(value)
            )
        )
        return NOT_SET

    def validate_value(self, value):
        if self.is_value_valid_type(value):
            return

        raise InvalidValueType(self.valid_value_types, type(value), self.path)

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
    def log(self):
        """Auto created logger for debugging."""
        if self._log is None:
            self._log = PypeLogger.get_logger(self.__class__.__name__)
        return self._log

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

    @abstractmethod
    def save(self):
        """Save data for current state."""
        pass

    @abstractmethod
    def item_initalization(self):
        pass

    @abstractproperty
    def value(self):
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
    def add_to_studio_default(self):
        """Item's implementation to set current values as studio's overrides.

        Mark item and it's children as they have studio overrides.
        """
        pass

    def remove_from_studio_default(self, on_change_trigger=None):
        if self.override_state is not OverrideState.STUDIO:
            return

        initialized = False
        if on_change_trigger is None:
            initialized = True
            on_change_trigger = []

        self._remove_from_studio_default(on_change_trigger)

        if initialized:
            for callback in on_change_trigger:
                callback()

    @abstractmethod
    def _remove_from_studio_default(self, on_change_trigger):
        """Item's implementation to remove studio overrides.

        Mark item as it does not have studio overrides unset studio
        override values.
        """
        pass

    def remove_from_project_override(self, on_change_trigger=None):
        if self.override_state is not OverrideState.PROJECT:
            return

        initialized = False
        if on_change_trigger is None:
            initialized = True
            on_change_trigger = []

        self._remove_from_project_override(on_change_trigger)

        if initialized:
            for callback in on_change_trigger:
                callback()

    @abstractmethod
    def add_to_project_override(self):
        """Item's implementation to set values as overriden for project.

        Mark item and all it's children as they're overriden. Must skip
        items with children items that has attributes `is_group`
        and `any_parent_is_group` set to False. In that case those items
        are not meant to be overridable and should trigger the method on it's
        children.

        """
        pass

    @abstractmethod
    def _remove_from_project_override(self, on_change_trigger):
        """Item's implementation to remove project overrides.

        Mark item as does not have project overrides. Must not change
        `was_overriden` attribute value.
        """
        pass

    def reset_callbacks(self):
        """Clear any callbacks that are registered."""
        self.on_change_callbacks = []


class ItemEntity(BaseItemEntity):
    def __init__(self, *args, **kwargs):
        super(ItemEntity, self).__init__(*args, **kwargs)

        self.is_file = self.schema_data.get("is_file", False)
        self.is_group = self.schema_data.get("is_group", False)
        self.is_in_dynamic_item = bool(
            not self.is_dynamic_item
            and (self.parent.is_dynamic_item or self.parent.is_in_dynamic_item)
        )

        # Dynamic item can't have key defined in it-self
        # - key is defined by it's parent
        if self.is_dynamic_item:
            self.require_key = False

        # If value should be stored to environments
        self.env_group_key = self.schema_data.get("env_group_key")
        self.is_env_group = bool(self.env_group_key is not None)

        self.create_schema_object = self.parent.create_schema_object

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

        self.key = self.schema_data.get("key")
        self.label = self.schema_data.get("label")

        self.item_initalization()

    def save(self):
        """Call save on root item."""
        self.root_item.save()

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
