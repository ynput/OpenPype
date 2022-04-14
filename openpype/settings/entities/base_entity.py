from uuid import uuid4
from abc import ABCMeta, abstractmethod, abstractproperty

import six

from .lib import (
    NOT_SET,
    OverrideState
)

from .exceptions import (
    BaseInvalidValue,
    InvalidValueType,
    SchemeGroupHierarchyBug,
    EntitySchemaError
)

from openpype.lib import PypeLogger


@six.add_metaclass(ABCMeta)
class BaseEntity:
    """Base entity class for Setting's item type workflow.

    Args:
        schema_data (dict): Schema data that defines entity behavior.
    """

    def __init__(self, schema_data, *args, **kwargs):
        self.schema_data = schema_data
        tooltip = None
        if schema_data:
            tooltip = schema_data.get("tooltip")
        self.tooltip = tooltip

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

    schema_types = ["separator", "splitter", "label"]

    def __getitem__(self, key):
        return self.schema_data[key]

    def schema_validations(self):
        """TODO validate GUI schemas."""
        pass


class BaseItemEntity(BaseEntity):
    """Base of item entity that is not only for GUI but can modify values.

    Defines minimum attributes of all entities that are not `gui_type`.

    Args:
        schema_data (dict): Schema data that defines entity behavior.
    """
    gui_type = False

    def __init__(self, schema_data):
        super(BaseItemEntity, self).__init__(schema_data)

        # Parent entity
        self.parent = None

        # Entity is dynamically created (in list or dict with mutable keys)
        #   - can be also dynamically removed
        self.is_dynamic_item = False

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
        # Default values are not stored to an openpype file
        # - these must not be set through schemas directly
        self.dynamic_schema_id = None
        self.is_dynamic_schema_node = False
        self.is_in_dynamic_schema_node = False

        # Reference to parent entity which has `is_group` == True
        #   - stays as None if none of parents is group
        self.group_item = None
        # Reference to parent entity which has `is_file` == True
        self.file_item = None
        # Reference to `RootEntity`
        self.root_item = None
        # Change of value requires restart of OpenPype
        self._require_restart_on_change = False

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
        self._override_state = OverrideState.NOT_DEFINED
        self._ignore_missing_defaults = None

        # These attributes may change values during existence of an object
        # Default value, studio override values and project override values
        # - these should be set only with `update_default_value` etc.
        # TODO convert to private attributes
        self._default_value = NOT_SET
        self._studio_override_value = NOT_SET
        self._project_override_value = NOT_SET

        # Entity has set `_default_value` (is not NOT_SET)
        self.has_default_value = False

        # Entity is marked as it contain studio override data so it's value
        #   will be stored to studio overrides. This is relevant attribute
        #   only if current override state is set to STUDIO.
        self._has_studio_override = False
        # Entity has set `_studio_override_value` (is not NOT_SET)
        self.had_studio_override = False

        # Entity is marked as it contain project override data so it's value
        #   will be stored to project overrides. This is relevant attribute
        #   only if current override state is set to PROJECT.
        self._has_project_override = False
        # Entity has set `_project_override_value` (is not NOT_SET)
        self.had_project_override = False

        self._default_log_invalid_types = True
        self._studio_log_invalid_types = True
        self._project_log_invalid_types = True

        # Callbacks that are called on change.
        # - main current purspose is to register GUI callbacks
        self.on_change_callbacks = []

        roles = schema_data.get("roles")
        if roles is None:
            roles = []
        elif not isinstance(roles, list):
            roles = [roles]
        self.roles = roles

    @abstractmethod
    def collect_static_entities_by_path(self):
        """Collect all paths of all static path entities.

        Static path is entity which is not dynamic or under dynamic entity.
        """
        pass

    @property
    def require_restart_on_change(self):
        return self._require_restart_on_change

    @property
    def require_restart(self):
        return False

    @property
    def has_studio_override(self):
        """Says if entity or it's children has studio overrides."""
        if self._override_state >= OverrideState.STUDIO:
            return self._has_studio_override
        return False

    @property
    def has_project_override(self):
        """Says if entity or it's children has project overrides."""
        if self._override_state >= OverrideState.PROJECT:
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

    @abstractmethod
    def get_entity_from_path(self, path):
        """Return system settings entity."""
        pass

    @abstractmethod
    def has_child_with_key(self, key):
        """Entity contains key as children."""
        pass

    def schema_validations(self):
        """Validate schema of entity and it's hierachy.

        Contain default validations same for all entities.
        """
        # Entity must have defined valid value types.
        if self.valid_value_types is NOT_SET:
            raise EntitySchemaError(
                self, "Attribute `valid_value_types` is not filled."
            )

        # Check if entity has defined key when is required.
        if self.require_key and not self.key:
            error_msg = "Missing \"key\" in schema data. {}".format(
                str(self.schema_data).replace("'", '"')
            )
            raise EntitySchemaError(self, error_msg)

        # Group entity must have defined label. (UI specific)
        # QUESTION this should not be required?
        if not self.label and self.is_group:
            raise EntitySchemaError(
                self, "Item is set as `is_group` but has empty `label`."
            )

        # Group item can be only once in on hierarchy branch.
        if self.is_group and self.group_item is not None:
            raise SchemeGroupHierarchyBug(self)

        # Group item can be only once in on hierarchy branch.
        if self.group_item is not None and self.is_dynamic_schema_node:
            reason = (
                "Dynamic schema is inside grouped item {}."
                " Change group hierarchy or remove dynamic"
                " schema to be able work properly."
            ).format(self.group_item.path)
            raise EntitySchemaError(self, reason)

        # Validate that env group entities will be stored into file.
        #   - env group entities must store metadata which is not possible if
        #       metadata would be outside of file
        if self.file_item is None and self.is_env_group:
            reason = (
                "Environment item is not inside file"
                " item so can't store metadata for defaults."
            )
            raise EntitySchemaError(self, reason)

        # Dynamic items must not have defined labels. (UI specific)
        if self.label and self.is_dynamic_item:
            raise EntitySchemaError(
                self, "Item has set label but is used as dynamic item."
            )

        # Dynamic items or items in dynamic item must not have set `is_group`
        if self.is_group and (self.is_dynamic_item or self.is_in_dynamic_item):
            raise EntitySchemaError(
                self, "Dynamic entity has set `is_group` to true."
            )

        if (
            self.require_restart_on_change
            and (self.is_dynamic_item or self.is_in_dynamic_item)
        ):
            raise EntitySchemaError(
                self, "Dynamic entity can't require restart."
            )

    @abstractproperty
    def root_key(self):
        """Root is represented as this dictionary key."""
        pass

    @abstractmethod
    def set_override_state(self, state, ignore_missing_defaults):
        """Set override state and trigger it on children.

        Method discard all changes in hierarchy and use values, metadata
        and all kind of values for defined override state. May be used to
        apply updated values (default, studio overrides, project overrides).

        Should start on root entity and when triggered then must be called on
        all entities in hierarchy.

        Argument `ignore_missing_defaults` should be used when entity has
        children that are not saved or used all the time but override statu
        must be changed and children must have any default value.

        Args:
            state (OverrideState): State to which should be data changed.
            ignore_missing_defaults (bool): Ignore missing default values.
                Entity won't raise `DefaultsNotDefined` and
                `StudioDefaultsNotDefined`.
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
        return isinstance(value, self.valid_value_types)

    def _validate_value_type(self, value):
        """Validate entered value.

        Raises:
            InvalidValueType: If value's type is not valid by entity's
                definition.
        """
        if self.is_value_valid_type(value):
            return

        raise InvalidValueType(self.valid_value_types, type(value), self.path)

    def _convert_to_valid_type(self, value):
        """Private method of entity to convert value.

        NOTE: Method is not abstract as more entities won't have implemented
            logic inside.

        Must return NOT_SET if can't convert the value.
        """
        return NOT_SET

    def convert_to_valid_type(self, value):
        """Check value type with possibility of conversion to valid.

        If entered value has right type than is returned as it is. otherwise
        is used privete method of entity to try convert.

        Raises:
            InvalidValueType: If value's type is not valid by entity's
                definition and can't be converted by entity logic.
        """
        #
        if self.is_value_valid_type(value):
            return value

        new_value = self._convert_to_valid_type(value)
        if new_value is not NOT_SET and self.is_value_valid_type(new_value):
            return new_value

        raise InvalidValueType(self.valid_value_types, type(value), self.path)

    # TODO convert to private method
    def _check_update_value(self, value, value_source, log_invalid_types=True):
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

        try:
            new_value = self.convert_to_valid_type(value)
        except BaseInvalidValue:
            new_value = NOT_SET

        if new_value is not NOT_SET:
            return new_value

        if log_invalid_types:
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

    @abstractmethod
    def settings_value(self):
        """Value of an item without key without dynamic items."""
        pass

    @abstractmethod
    def collect_dynamic_schema_entities(self):
        """Collect entities that are on top of dynamically added schemas.

        This method make sence only when defaults are saved.
        """
        pass

    @abstractmethod
    def save(self):
        """Save data for current state."""
        pass

    @abstractmethod
    def _item_initialization(self):
        """Entity specific initialization process."""
        pass

    @abstractproperty
    def value(self):
        """Value of entity without metadata."""
        pass

    @property
    def _can_discard_changes(self):
        """Defines if `discard_changes` will be processed."""
        return self.has_unsaved_changes

    @property
    def _can_add_to_studio_default(self):
        """Defines if `add_to_studio_default` will be processed."""
        if self._override_state is not OverrideState.STUDIO:
            return False

        # Skip if entity is under group
        if self.group_item is not None:
            return False

        # Skip if is group and any children is already marked with studio
        #   overrides
        if self.is_group and self.has_studio_override:
            return False
        return True

    @property
    def _can_remove_from_studio_default(self):
        """Defines if `remove_from_studio_default` can be processed."""
        if self._override_state is not OverrideState.STUDIO:
            return False

        if not self.has_studio_override:
            return False
        return True

    @property
    def _can_add_to_project_override(self):
        """Defines if `add_to_project_override` can be processed."""
        # Show only when project overrides are set
        if self._override_state is not OverrideState.PROJECT:
            return False

        # Do not show on items under group item
        if self.group_item is not None:
            return False

        # Skip if already is marked to save project overrides
        if self.is_group and self.has_project_override:
            return False
        return True

    @property
    def _can_remove_from_project_override(self):
        """Defines if `remove_from_project_override` can be processed."""
        if self._override_state is not OverrideState.PROJECT:
            return False

        # Dynamic items can't have these actions
        if self.is_dynamic_item or self.is_in_dynamic_item:
            return False

        if not self.has_project_override:
            return False
        return True

    @property
    def can_trigger_discard_changes(self):
        """Defines if can trigger `discard_changes`.

        Also can be used as validation before the method is called.
        """
        return self._can_discard_changes

    @property
    def can_trigger_add_to_studio_default(self):
        """Defines if can trigger `add_to_studio_default`.

        Also can be used as validation before the method is called.
        """
        if self.is_dynamic_item or self.is_in_dynamic_item:
            return False
        return self._can_add_to_studio_default

    @property
    def can_trigger_remove_from_studio_default(self):
        """Defines if can trigger `remove_from_studio_default`.

        Also can be used as validation before the method is called.
        """
        if self.is_dynamic_item or self.is_in_dynamic_item:
            return False
        return self._can_remove_from_studio_default

    @property
    def can_trigger_add_to_project_override(self):
        """Defines if can trigger `add_to_project_override`.

        Also can be used as validation before the method is called.
        """
        if self.is_dynamic_item or self.is_in_dynamic_item:
            return False
        return self._can_add_to_project_override

    @property
    def can_trigger_remove_from_project_override(self):
        """Defines if can trigger `remove_from_project_override`.

        Also can be used as validation before the method is called.
        """
        if self.is_dynamic_item or self.is_in_dynamic_item:
            return False
        return self._can_remove_from_project_override

    def discard_changes(self, on_change_trigger=None):
        """Discard changes on entity and it's children.

        Reset all values to same values as had when `set_override_state` was
        called last time.

        Must not affect `had_studio_override` value or `had_project_override`
        value. It must be marked that there are keys/values which are not in
        defaults or overrides.

        Won't affect if will be stored as overrides if entity is under
        group entity in hierarchy.

        This is wrapper method that handles on_change callbacks only when all
        `_discard_changes` on all children happened. That is important as
        value changes may trigger change callbacks that must be ignored.
        Callbacks are triggered by entity where method was called.

        Args:
            on_change_trigger (list): Callbacks of `on_change` should be stored
                to trigger them afterwards.
        """
        initialized = False
        if on_change_trigger is None:
            if not self.can_trigger_discard_changes:
                return

            initialized = True
            on_change_trigger = []

        self._discard_changes(on_change_trigger)

        if initialized:
            for callback in on_change_trigger:
                callback()

    @abstractmethod
    def _discard_changes(self, on_change_trigger):
        """Entity's implementation to discard all changes made by user."""
        pass

    def add_to_studio_default(self, on_change_trigger=None):
        initialized = False
        if on_change_trigger is None:
            if not self.can_trigger_add_to_studio_default:
                return

            initialized = True
            on_change_trigger = []

        self._add_to_studio_default(on_change_trigger)

        if initialized:
            for callback in on_change_trigger:
                callback()

    @abstractmethod
    def _add_to_studio_default(self, on_change_trigger):
        """Item's implementation to set current values as studio's overrides.

        Mark item and it's children as they have studio overrides.
        """
        pass

    def remove_from_studio_default(self, on_change_trigger=None):
        """Remove studio overrides from entity and it's children.

        Reset values to openpype's default and mark entity to not store values
        as studio overrides if entity is not under group.

        This is wrapper method that handles on_change callbacks only when all
        `_remove_from_studio_default` on all children happened. That is
        important as value changes may trigger change callbacks that must be
        ignored. Callbacks are triggered by entity where method was called.

        Args:
            on_change_trigger (list): Callbacks of `on_change` should be stored
                to trigger them afterwards.
        """
        initialized = False
        if on_change_trigger is None:
            if not self.can_trigger_remove_from_studio_default:
                return

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

    def add_to_project_override(self, on_change_trigger=None):
        initialized = False
        if on_change_trigger is None:
            if not self.can_trigger_add_to_project_override:
                return

            initialized = True
            on_change_trigger = []

        self._add_to_project_override(on_change_trigger)

        if initialized:
            for callback in on_change_trigger:
                callback()

    @abstractmethod
    def _add_to_project_override(self, on_change_trigger):
        """Item's implementation to set values as overridden for project.

        Mark item and all it's children to be stored as project overrides.
        """
        pass

    def remove_from_project_override(self, on_change_trigger=None):
        """Remove project overrides from entity and it's children.

        Reset values to studio overrides or openpype's default and mark entity
        to not store values as project overrides if entity is not under group.

        This is wrapper method that handles on_change callbacks only when all
        `_remove_from_project_override` on all children happened. That is
        important as value changes may trigger change callbacks that must be
        ignored. Callbacks are triggered by entity where method was called.

        Args:
            on_change_trigger (list): Callbacks of `on_change` should be stored
                to trigger them afterwards.
        """
        if self._override_state is not OverrideState.PROJECT:
            return

        initialized = False
        if on_change_trigger is None:
            if not self.can_trigger_remove_from_project_override:
                return
            initialized = True
            on_change_trigger = []

        self._remove_from_project_override(on_change_trigger)

        if initialized:
            for callback in on_change_trigger:
                callback()

    @abstractmethod
    def _remove_from_project_override(self, on_change_trigger):
        """Item's implementation to remove project overrides.

        Mark item as does not have project overrides. Must not change
        `was_overridden` attribute value.

        Args:
            on_change_trigger (list): Callbacks of `on_change` should be stored
                to trigger them afterwards.
        """
        pass

    def reset_callbacks(self):
        """Clear any registered callbacks on entity and all children."""
        self.on_change_callbacks = []


class ItemEntity(BaseItemEntity):
    """Item that is used as hierarchical entity.

    Entity must have defined parent and can't be created outside it's parent.

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
    _default_label_wrap = {
        "use_label_wrap": False,
        "collapsible": True,
        "collapsed": False
    }

    def __init__(self, schema_data, parent, is_dynamic_item=False):
        super(ItemEntity, self).__init__(schema_data)

        self.parent = parent
        self.is_dynamic_item = is_dynamic_item

        self.is_file = self.schema_data.get("is_file", False)
        # These keys have underscore as they must not be set in schemas
        self.dynamic_schema_id = self.schema_data.get(
            "_dynamic_schema_id", None
        )
        self.is_dynamic_schema_node = self.dynamic_schema_id is not None

        self.is_group = self.schema_data.get("is_group", False)
        self.is_in_dynamic_item = bool(
            not self.is_dynamic_item
            and (self.parent.is_dynamic_item or self.parent.is_in_dynamic_item)
        )

        # Dynamic item can't have key defined in it-self
        # - key is defined by it's parent
        if self.is_dynamic_item:
            self.require_key = False

        # If value should be stored to environments and uder which group key
        # - the key may be dynamically changed by it's parent on save
        self.env_group_key = self.schema_data.get("env_group_key")
        self.is_env_group = bool(self.env_group_key is not None)

        # Root item reference
        self.root_item = self.parent.root_item

        # Item require restart on value change
        require_restart_on_change = self.schema_data.get("require_restart")
        if (
            require_restart_on_change is None
            and not (self.is_dynamic_item or self.is_in_dynamic_item)
        ):
            require_restart_on_change = self.parent.require_restart_on_change
        self._require_restart_on_change = require_restart_on_change

        # File item reference
        if not self.is_dynamic_schema_node:
            self.is_in_dynamic_schema_node = (
                self.parent.is_dynamic_schema_node
                or self.parent.is_in_dynamic_schema_node
            )

        if (
            not self.is_dynamic_schema_node
            and not self.is_in_dynamic_schema_node
        ):
            if self.parent.is_file:
                self.file_item = self.parent
            elif self.parent.file_item:
                self.file_item = self.parent.file_item

        # Group item reference
        if self.parent.is_group:
            self.group_item = self.parent

        elif self.parent.group_item is not None:
            self.group_item = self.parent.group_item

        self.key = self.schema_data.get("key")
        self.label = self.schema_data.get("label")

        # GUI attributes
        _default_label_wrap = self.__class__._default_label_wrap
        for key, value in ItemEntity._default_label_wrap.items():
            if key not in _default_label_wrap:
                self.log.warning(
                    "Class {} miss default label wrap key \"{}\"".format(
                        self.__class__.__name__, key
                    )
                )
                _default_label_wrap[key] = value

        use_label_wrap = self.schema_data.get("use_label_wrap")
        if use_label_wrap is None:
            if not self.label:
                use_label_wrap = False
            else:
                use_label_wrap = _default_label_wrap["use_label_wrap"]
        self.use_label_wrap = use_label_wrap

        # Used only if `use_label_wrap` is set to True
        self.collapsible = self.schema_data.get(
            "collapsible",
            _default_label_wrap["collapsible"]
        )
        self.collapsed = self.schema_data.get(
            "collapsed",
            _default_label_wrap["collapsed"]
        )

        self._item_initialization()

    def save(self):
        """Call save on root item."""
        self.root_item.save()

    @property
    def root_key(self):
        return self.root_item.root_key

    @abstractmethod
    def collect_dynamic_schema_entities(self, collector):
        """Collect entities that are on top of dynamically added schemas.

        This method make sence only when defaults are saved.

        Args:
            collector(DynamicSchemaValueCollector): Object where dynamic
                entities are stored.
        """
        pass

    def schema_validations(self):
        if not self.label and self.use_label_wrap:
            reason = (
                "Entity has set `use_label_wrap` to true but"
                " does not have set `label`."
            )
            raise EntitySchemaError(self, reason)

        if (
            not self.is_dynamic_schema_node
            and not self.is_in_dynamic_schema_node
            and self.is_file
            and self.file_item is not None
        ):
            reason = (
                "Entity has set `is_file` to true but"
                " it's parent is already marked as file item."
            )
            raise EntitySchemaError(self, reason)

        super(ItemEntity, self).schema_validations()

    def create_schema_object(self, *args, **kwargs):
        """Reference method for creation of entities defined in RootEntity."""
        return self.schema_hub.create_schema_object(*args, **kwargs)

    @property
    def schema_hub(self):
        return self.root_item.schema_hub

    def get_entity_from_path(self, path):
        return self.root_item.get_entity_from_path(path)

    @abstractmethod
    def update_default_value(self, parent_values, log_invalid_types=True):
        """Fill default values on startup or on refresh.

        Default values stored in `openpype` repository should update all items
        in schema. Each item should take values for his key and set it's value
        or pass values down to children items.

        Args:
            parent_values (dict): Values of parent's item. But in case item is
                used as widget, `parent_values` contain value for item.
            log_invalid_types (bool): Log invalid type of value. Used when
                entity can have children with same keys and different types.
        """
        pass

    @abstractmethod
    def update_studio_value(self, parent_values, log_invalid_types=True):
        """Fill studio override values on startup or on refresh.

        Set studio value if is not set to NOT_SET, in that case studio
        overrides are not set yet.

        Args:
            parent_values (dict): Values of parent's item. But in case item is
                used as widget, `parent_values` contain value for item.
            log_invalid_types (bool): Log invalid type of value. Used when
                entity can have children with same keys and different types.
        """
        pass

    @abstractmethod
    def update_project_value(self, parent_values, log_invalid_types=True):
        """Fill project override values on startup, refresh or project change.

        Set project value if is not set to NOT_SET, in that case project
        overrides are not set yet.

        Args:
            parent_values (dict): Values of parent's item. But in case item is
                used as widget, `parent_values` contain value for item.
            log_invalid_types (bool): Log invalid type of value. Used when
                entity can have children with same keys and different types.
        """
        pass
