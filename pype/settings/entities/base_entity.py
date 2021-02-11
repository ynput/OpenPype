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
    """Base entity class for Setting's item type workflow.

    Args:
        schema_data (dict): Schema data that defines entity behavior.
    """

    def __init__(self, schema_data, *args, **kwargs):
        self.schema_data = schema_data

        # Entity id
        self._id = uuid4()

    def __hash__(self):
        """Make entity hashable by it's id.

        Helps to store entities as keys in dictionary.
        """
        return self.id

    @property
    def id(self):
        """Unified identifier of an entity."""
        return self._id

    @abstractproperty
    def gui_type(self):
        """Is entity GUI type entity."""
        pass

    @abstractmethod
    def schema_validations(self):
        """Validation of schema."""
        pass


class GUIEntity(BaseEntity):
    """Entity without any specific logic that should be handled only in GUI."""
    gui_type = True

    schema_types = ["divider", "splitter", "label"]

    def __getitem__(self, key):
        return self.schema_data[key]

    def schema_validations(self):
        """TODO validate GUI schemas."""
        pass


class BaseItemEntity(BaseEntity):
    """Base of item entity that is not only for GUI but can modify values.

    Defines minimum attributes of all entities that are not `gui_type`.

    Dynamically created entity is entity that can be removed from settings
    hierarchy and it's key or existence is not defined in schemas. Are
    created by `ListEntity` or `DictMutableKeysEntity`. Their information about
    default value or modification is not relevant.

    Args:
        schema_data (dict): Schema data that defines entity behavior.
        parent (BaseItemEntity): Parent entity that created this entity.
        is_dynamic_item (bool): Entity should behave like dynamically created
            entity.
    """
    gui_type = False

    def __init__(self, schema_data, parent=None, is_dynamic_item=False):
        super(BaseItemEntity, self).__init__(schema_data)

        # Parent entity
        self.parent = parent

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

        # Override state defines which values are used, saved and how.
        # TODO convert to private attribute
        self.override_state = OverrideState.NOT_DEFINED

        # These attributes may change values during existence of an object
        # Default value, studio override values and project override values
        # - these should be set only with `update_default_value` etc.
        # TODO convert to private attributes
        self.default_value = NOT_SET
        self.studio_override_value = NOT_SET
        self.project_override_value = NOT_SET

        # Entity has set `default_value` (is not NOT_SET)
        self.has_default_value = False

        # Entity is marked as it contain studio override data so it's value
        #   will be stored to studio overrides. This is relevant attribute
        #   only if current override state is set to STUDIO.
        self._has_studio_override = False
        # Entity has set `studio_override_values` (is not NOT_SET)
        self.had_studio_override = False

        # Entity is marked as it contain project override data so it's value
        #   will be stored to project overrides. This is relevant attribute
        #   only if current override state is set to PROJECT.
        self._has_project_override = False
        # Entity has set `project_override_value` (is not NOT_SET)
        self.had_project_override = False

        # Callbacks that are called on change.
        # - main current purspose is to register GUI callbacks
        self.on_change_callbacks = []

        roles = schema_data.get("roles")
        if roles is None and parent:
            roles = parent.roles
        elif not isinstance(roles, list):
            roles = [roles]
        self.roles = roles

    @property
    def has_studio_override(self):
        """Says if entity or it's children has studio overrides."""
        if self.override_state >= OverrideState.STUDIO:
            return self._has_studio_override
        return False

    @property
    def has_project_override(self):
        """Says if entity or it's children has project overrides."""
        if self.override_state >= OverrideState.PROJECT:
            return self._has_project_override
        return False

    @property
    def path(self):
        """Full path of an entity in settings hierarchy.

        It is not possible to use this attribute during initialization because
        initialization happens before entity is added to parent's children.
        """
        if self._path is not None:
            return self._path

        path = self.parent.get_child_path(self)
        if not self.is_in_dynamic_item and not self.is_dynamic_item:
            self._path = path
        return path

    @abstractmethod
    def get_child_path(self, child_entity):
        """Return path for a direct child entity."""
        pass

    def schema_validations(self):
        """Validate schema of entity and it's hierachy.

        Contain default validations same for all entities.
        """
        # Entity must have defined valid value types.
        if self.valid_value_types is NOT_SET:
            raise ValueError("Attribute `valid_value_types` is not filled.")

        # Check if entity has defined key when is required.
        if self.require_key and not self.key:
            error_msg = "{}: Missing \"key\" in schema data. {}".format(
                self.path, str(self.schema_data).replace("'", '"')
            )
            raise KeyError(error_msg)

        # Group entity must have defined label. (UI specific)
        # QUESTION this should not be required?
        if not self.label and self.is_group:
            raise ValueError(
                "{}: Item is set as `is_group` but has empty `label`.".format(
                    self.path
                )
            )

        # Group item can be only once in on hierarchy branch.
        if self.is_group and self.group_item:
            raise SchemeGroupHierarchyBug(self.path)

        # Validate that env group entities will be stored into file.
        #   - env group entities must store metadata which is not possible if
        #       metadata would be outside of file
        if not self.file_item and self.is_env_group:
            raise ValueError((
                "{}: Environment item is not inside file"
                " item so can't store metadata for defaults."
            ).format(self.path))

        # Dynamic items must not have defined labels. (UI specific)
        if self.label and self.is_dynamic_item:
            raise ValueError((
                "{}: Item has set label but is used as dynamic item."
            ).format(self.path))

    @abstractmethod
    def set_override_state(self, state):
        """This method should set override state and refresh data.

        Discard all changes in hierarchy and use values, metadata and
        all kind of states for defined state.

        Always should start on root entity and when triggered them must be
        called on all entities in hierarchy.

        TODO: add validation that parent's state is same as want to set.
        """
        pass

    @abstractmethod
    def on_change(self):
        """Trigger change callbacks and tell parent that has changed.

        Can be any kind of change. Value has changed, has studio overrides
        changed from True to False, etc.
        """
        pass

    @abstractmethod
    def on_child_change(self, child_entity):
        """Triggered by children when they've changed.

        Args:
            child_entity (BaseItemEntity): Direct child entity that has
                changed.
        """
        pass

    @abstractmethod
    def set(self, value):
        """Set value of entity.

        Args:
            value (Any): Setter of value for this entity.
        """
        pass

    def is_value_valid_type(self, value):
        """Validate passed value type by entity's defined valid types.

        Returns:
            bool: True if value is in entity's defined types.
        """
        value_type = type(value)
        for valid_type in self.valid_value_types:
            if value_type is valid_type:
                return True
        return False

    def validate_value(self, value):
        """Validate entered value.

        Raises:
            InvalidValueType: If value's type is not valid by entity's
                definition.
        """
        if self.is_value_valid_type(value):
            return

        raise InvalidValueType(self.valid_value_types, type(value), self.path)

    # TODO convert to private method
    def check_update_value(self, value, value_source):
        """Validation of value on update methods.

        Update methods update data from currently saved settings so it is
        possible to have invalid type mainly during development.

        Args:
            value (Any): Value that got to update method.
            value_source (str): Source update method. Is used for logging and
                is not used as part of logic ("default", "studio override",
                "project override").

        Returns:
            Any: Return value itself if has valid type.
            NOT_SET: If value has invalid type.
        """
        # Nothing to validate if is NOT_SET
        if value is NOT_SET:
            return value

        # Validate value type and return value itself if is valid.
        if self.is_value_valid_type(value):
            return value

        # Warning log about invalid value type.
        self.log.warning(
            (
                "{} Got invalid value type for {} values."
                " Expected types: {} | Got Type: {} | Value: \"{}\""
            ).format(
                self.path, value_source,
                self.valid_value_types, type(value), str(value)
            )
        )
        return NOT_SET

    def available_for_role(self, role_name=None):
        """Is entity valid for role.

        Args:
            role_name (str): Name of role that will be validated. Entity's
                `user_role` attribute is used if not defined.

        Returns:
            bool: True if is available for role.
        """
        if not self.roles:
            return True
        if role_name is None:
            role_name = self.user_role
        return role_name in self.roles

    @property
    def user_role(self):
        """Entity is using user role.

        Returns:
            str: user role as string.

        """
        return self.parent.user_role

    @property
    def log(self):
        """Auto created logger for debugging or warnings."""
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
