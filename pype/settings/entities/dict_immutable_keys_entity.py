import copy

from .lib import (
    WRAPPER_TYPES,
    OverrideState,
    NOT_SET
)
from pype.settings.constants import (
    METADATA_KEYS,
    M_OVERRIDEN_KEY
)
from . import (
    BaseItemEntity,
    ItemEntity,
    BoolEntity,
    GUIEntity
)
from .exceptions import SchemaDuplicatedKeys


class DictImmutableKeysEntity(ItemEntity):
    """Entity that represents dictionary with predefined keys.

    Entity's keys can't be removed or added and children type is defined in
    schema data.

    It is possible to use entity similar way as `dict` object. Returned values
    are not real settings values but entities representing the value.
    """
    schema_types = ["dict"]
    _default_label_wrap = {
        "use_label_wrap": True,
        "collapsible": True,
        "collapsed": True
    }

    def __getitem__(self, key):
        """Return entity inder key."""
        return self.non_gui_children[key]

    def __setitem__(self, key, value):
        """Set value of item under key."""
        child_obj = self.non_gui_children[key]
        child_obj.set(value)

    def __iter__(self):
        """Iter through keys."""
        for key in self.keys():
            yield key

    def __contains__(self, key):
        """Check if key is available."""
        return key in self.non_gui_children

    def get(self, key, default=None):
        """Safe entity getter by key."""
        return self.non_gui_children.get(key, default)

    def keys(self):
        """Entity's keys."""
        return self.non_gui_children.keys()

    def values(self):
        """Children entities."""
        return self.non_gui_children.values()

    def items(self):
        """Children entities paired with their key (key, value)."""
        return self.non_gui_children.items()

    def set(self, value):
        """Set value."""
        new_value = self.convert_to_valid_type(value)
        for _key, _value in new_value.items():
            self.non_gui_children[_key].set(_value)

    def schema_validations(self):
        """Validation of schema data."""
        children_keys = set()
        for child_entity in self.children:
            if not isinstance(child_entity, BaseItemEntity):
                continue
            elif child_entity.key not in children_keys:
                children_keys.add(child_entity.key)
            else:
                raise SchemaDuplicatedKeys(self.path, child_entity.key)

        if self.checkbox_key:
            checkbox_child = self.non_gui_children.get(self.checkbox_key)
            if not checkbox_child:
                raise ValueError(
                    "{}: Checkbox children \"{}\" was not found.".format(
                        self.path, self.checkbox_key
                    )
                )
            if not isinstance(checkbox_child, BoolEntity):
                raise TypeError((
                    "{}: Checkbox children \"{}\" is not `boolean` type."
                ).format(self.path, self.checkbox_key))

        super(DictImmutableKeysEntity, self).schema_validations()
        # Trigger schema validation on children entities
        for child_obj in self.children:
            child_obj.schema_validations()

    def on_change(self):
        """Update metadata on change and pass change to parent."""
        self._update_current_metadata()

        for callback in self.on_change_callbacks:
            callback()
        self.parent.on_child_change(self)

    def on_child_change(self, _child_obj):
        """Trigger on change callback if child changes are not ignored."""
        if not self._ignore_child_changes:
            self.on_change()

    def _add_children(self, schema_data, first=True):
        """Add children from schema data and separate gui wrappers.

        Wrappers are stored in way so tool can create them and keep relation
        to entities.

        Args:
            schema_data (dict): Schema data of an entity.
            first (bool): Helper to know if was method called from inside of
                method when handling gui wrappers.
        """
        added_children = []
        for children_schema in schema_data["children"]:
            if children_schema["type"] in WRAPPER_TYPES:
                _children_schema = copy.deepcopy(children_schema)
                wrapper_children = self._add_children(
                    children_schema, False
                )
                _children_schema["children"] = wrapper_children
                added_children.append(_children_schema)
                continue

            child_obj = self.create_schema_object(children_schema, self)
            self.children.append(child_obj)
            added_children.append(child_obj)
            if isinstance(child_obj, GUIEntity):
                continue

            self.non_gui_children[child_obj.key] = child_obj

        if not first:
            return added_children

        for child_obj in added_children:
            self.gui_layout.append(child_obj)

    def _item_initalization(self):
        self._default_metadata = NOT_SET
        self._studio_override_metadata = NOT_SET
        self._project_override_metadata = NOT_SET

        self._ignore_child_changes = False

        # `current_metadata` are still when schema is loaded
        # - only metadata stored with dict item are gorup overrides in
        #   M_OVERRIDEN_KEY
        self._current_metadata = {}
        self._metadata_are_modified = False

        # Children are stored by key as keys are immutable and are defined by
        # schema
        self.valid_value_types = (dict, )
        self.children = []
        self.non_gui_children = {}
        self.gui_layout = []
        self._add_children(self.schema_data)

        if self.is_dynamic_item:
            self.require_key = False

        # GUI attributes
        self.checkbox_key = self.schema_data.get("checkbox_key")
        self.highlight_content = self.schema_data.get(
            "highlight_content", False
        )
        self.show_borders = self.schema_data.get("show_borders", True)

    def get_child_path(self, child_obj):
        """Get hierarchical path of child entity.

        Child must be entity's direct children.
        """
        result_key = None
        for key, _child_obj in self.non_gui_children.items():
            if _child_obj is child_obj:
                result_key = key
                break

        if result_key is None:
            raise ValueError("Didn't found child {}".format(child_obj))

        return "/".join([self.path, result_key])

    def _update_current_metadata(self):
        current_metadata = {}
        for key, child_obj in self.non_gui_children.items():
            if self._override_state is OverrideState.DEFAULTS:
                break

            if not child_obj.is_group:
                continue

            if (
                self._override_state is OverrideState.STUDIO
                and not child_obj.has_studio_override
            ):
                continue

            if (
                self._override_state is OverrideState.PROJECT
                and not child_obj.has_project_override
            ):
                continue

            if M_OVERRIDEN_KEY not in current_metadata:
                current_metadata[M_OVERRIDEN_KEY] = []
            current_metadata[M_OVERRIDEN_KEY].append(key)

        # Define if current metadata are avaialble for current override state
        metadata = NOT_SET
        if self._override_state is OverrideState.STUDIO:
            metadata = self._studio_override_metadata

        elif self._override_state is OverrideState.PROJECT:
            metadata = self._project_override_metadata

        if metadata is NOT_SET:
            metadata = {}

        self._metadata_are_modified = current_metadata != metadata
        self._current_metadata = current_metadata

    def set_override_state(self, state):
        # Trigger override state change of root if is not same
        if self.root_item.override_state is not state:
            self.root_item.set_override_state(state)
            return

        # Change has/had override states
        self._override_state = state

        for child_obj in self.non_gui_children.values():
            child_obj.set_override_state(state)

        self._update_current_metadata()

    @property
    def value(self):
        output = {}
        for key, child_obj in self.non_gui_children.items():
            output[key] = child_obj.value
        return output

    @property
    def has_unsaved_changes(self):
        if self._metadata_are_modified:
            return True

        return self._child_has_unsaved_changes

    @property
    def _child_has_unsaved_changes(self):
        for child_obj in self.non_gui_children.values():
            if child_obj.has_unsaved_changes:
                return True
        return False

    @property
    def has_studio_override(self):
        return self._child_has_studio_override

    @property
    def _child_has_studio_override(self):
        if self._override_state >= OverrideState.STUDIO:
            for child_obj in self.non_gui_children.values():
                if child_obj.has_studio_override:
                    return True
        return False

    @property
    def has_project_override(self):
        return self._child_has_project_override

    @property
    def _child_has_project_override(self):
        if self._override_state >= OverrideState.PROJECT:
            for child_obj in self.non_gui_children.values():
                if child_obj.has_project_override:
                    return True
        return False

    def settings_value(self):
        if self._override_state is OverrideState.NOT_DEFINED:
            return NOT_SET

        if self._override_state is OverrideState.DEFAULTS:
            output = {}
            for key, child_obj in self.non_gui_children.items():
                child_value = child_obj.settings_value()
                if not child_obj.is_file and not child_obj.file_item:
                    for _key, _value in child_value.items():
                        new_key = "/".join([key, _key])
                        output[new_key] = _value
                else:
                    output[key] = child_value
            return output

        if self.is_group:
            if self._override_state is OverrideState.STUDIO:
                if not self.has_studio_override:
                    return NOT_SET
            elif self._override_state is OverrideState.PROJECT:
                if not self.has_project_override:
                    return NOT_SET

        output = {}
        for key, child_obj in self.non_gui_children.items():
            value = child_obj.settings_value()
            if value is not NOT_SET:
                output[key] = value

        if not output:
            return NOT_SET

        output.update(self._current_metadata)
        return output

    def _prepare_value(self, value):
        if value is NOT_SET:
            return NOT_SET, NOT_SET

        # Create copy of value before poping values
        value = copy.deepcopy(value)
        metadata = {}
        for key in METADATA_KEYS:
            if key in value:
                metadata[key] = value.pop(key)
        return value, metadata

    def update_default_value(self, value):
        """Update default values.

        Not an api method, should be called by parent.
        """
        value = self._check_update_value(value, "default")
        self.has_default_value = value is not NOT_SET
        # TODO add value validation
        value, metadata = self._prepare_value(value)
        self._default_metadata = metadata

        if value is NOT_SET:
            for child_obj in self.non_gui_children.values():
                child_obj.update_default_value(value)
            return

        value_keys = set(value.keys())
        expected_keys = set(self.non_gui_children)
        unknown_keys = value_keys - expected_keys
        if unknown_keys:
            self.log.warning(
                "{} Unknown keys in default values: {}".format(
                    self.path,
                    ", ".join("\"{}\"".format(key) for key in unknown_keys)
                )
            )

        for key, child_obj in self.non_gui_children.items():
            child_value = value.get(key, NOT_SET)
            child_obj.update_default_value(child_value)

    def update_studio_value(self, value):
        """Update studio override values.

        Not an api method, should be called by parent.
        """
        value = self._check_update_value(value, "studio override")
        value, metadata = self._prepare_value(value)
        self._studio_override_metadata = metadata
        self.had_studio_override = metadata is not NOT_SET

        if value is NOT_SET:
            for child_obj in self.non_gui_children.values():
                child_obj.update_studio_value(value)
            return

        value_keys = set(value.keys())
        expected_keys = set(self.non_gui_children)
        unknown_keys = value_keys - expected_keys
        if unknown_keys:
            self.log.warning(
                "{} Unknown keys in studio overrides: {}".format(
                    self.path,
                    ", ".join("\"{}\"".format(key) for key in unknown_keys)
                )
            )
        for key, child_obj in self.non_gui_children.items():
            child_value = value.get(key, NOT_SET)
            child_obj.update_studio_value(child_value)

    def update_project_value(self, value):
        """Update project override values.

        Not an api method, should be called by parent.
        """
        value = self._check_update_value(value, "project override")
        value, metadata = self._prepare_value(value)
        self._project_override_metadata = metadata
        self.had_project_override = metadata is not NOT_SET

        if value is NOT_SET:
            for child_obj in self.non_gui_children.values():
                child_obj.update_project_value(value)
            return

        value_keys = set(value.keys())
        expected_keys = set(self.non_gui_children)
        unknown_keys = value_keys - expected_keys
        if unknown_keys:
            self.log.warning(
                "{} Unknown keys in project overrides: {}".format(
                    self.path,
                    ", ".join("\"{}\"".format(key) for key in unknown_keys)
                )
            )

        for key, child_obj in self.non_gui_children.items():
            child_value = value.get(key, NOT_SET)
            child_obj.update_project_value(child_value)

    def _discard_changes(self, on_change_trigger):
        self._ignore_child_changes = True

        for child_obj in self.non_gui_children.values():
            child_obj.discard_changes(on_change_trigger)

        self._ignore_child_changes = False

    def _add_to_studio_default(self, on_change_trigger):
        self._ignore_child_changes = True
        for child_obj in self.non_gui_children.values():
            child_obj.add_to_studio_default(on_change_trigger)
        self._ignore_child_changes = False
        self.parent.on_child_change(self)

    def _remove_from_studio_default(self, on_change_trigger):
        self._ignore_child_changes = True
        for child_obj in self.non_gui_children.values():
            child_obj.remove_from_studio_default(on_change_trigger)
        self._ignore_child_changes = False

    def _add_to_project_override(self, _on_change_trigger):
        self._ignore_child_changes = True
        for child_obj in self.non_gui_children.values():
            child_obj.add_to_project_override(_on_change_trigger)
        self._ignore_child_changes = False
        self.parent.on_child_change(self)

    def _remove_from_project_override(self, on_change_trigger):
        if self._override_state is not OverrideState.PROJECT:
            return

        self._ignore_child_changes = True
        for child_obj in self.non_gui_children.values():
            child_obj.remove_from_project_override(on_change_trigger)
        self._ignore_child_changes = False

    def reset_callbacks(self):
        """Reset registered callbacks on entity and children."""
        super(DictImmutableKeysEntity, self).reset_callbacks()
        for child_entity in self.children:
            child_entity.reset_callbacks()
