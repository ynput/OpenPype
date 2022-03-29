import copy
import collections

from .lib import (
    WRAPPER_TYPES,
    OverrideState,
    NOT_SET,
    STRING_TYPE
)
from openpype.settings.constants import (
    METADATA_KEYS,
    M_OVERRIDDEN_KEY,
    KEY_REGEX
)
from . import (
    BaseItemEntity,
    ItemEntity,
    BoolEntity,
    GUIEntity
)
from .exceptions import (
    DefaultsNotDefined,
    SchemaDuplicatedKeys,
    EntitySchemaError,
    InvalidKeySymbols
)


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
                raise SchemaDuplicatedKeys(self, child_entity.key)

        for key in self.keys():
            if not KEY_REGEX.match(key):
                raise InvalidKeySymbols(self.path, key)

        if self.checkbox_key:
            checkbox_child = self.non_gui_children.get(self.checkbox_key)
            if not checkbox_child:
                reason = "Checkbox children \"{}\" was not found.".format(
                    self.checkbox_key
                )
                raise EntitySchemaError(self, reason)

            if not isinstance(checkbox_child, BoolEntity):
                reason = (
                    "Checkbox children \"{}\" is not `boolean` type."
                ).format(self.checkbox_key)
                raise EntitySchemaError(self, reason)

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
        children_deque = collections.deque()
        for _children_schema in schema_data["children"]:
            children_schemas = self.schema_hub.resolve_schema_data(
                _children_schema
            )
            for children_schema in children_schemas:
                children_deque.append(children_schema)

        while children_deque:
            children_schema = children_deque.popleft()
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

    def _item_initialization(self):
        self._default_metadata = NOT_SET
        self._studio_override_metadata = NOT_SET
        self._project_override_metadata = NOT_SET

        self._ignore_child_changes = False

        # `current_metadata` are still when schema is loaded
        # - only metadata stored with dict item are gorup overrides in
        #   M_OVERRIDDEN_KEY
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

    def has_child_with_key(self, key):
        return key in self.non_gui_children

    def collect_static_entities_by_path(self):
        output = {}
        if self.is_dynamic_item or self.is_in_dynamic_item:
            return output

        output[self.path] = self
        for children in self.non_gui_children.values():
            result = children.collect_static_entities_by_path()
            if result:
                output.update(result)
        return output

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

            if M_OVERRIDDEN_KEY not in current_metadata:
                current_metadata[M_OVERRIDDEN_KEY] = []
            current_metadata[M_OVERRIDDEN_KEY].append(key)

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

    def set_override_state(self, state, ignore_missing_defaults):
        # Trigger override state change of root if is not same
        if self.root_item.override_state is not state:
            self.root_item.set_override_state(state)
            return

        # Change has/had override states
        self._override_state = state
        self._ignore_missing_defaults = ignore_missing_defaults

        for child_obj in self.non_gui_children.values():
            child_obj.set_override_state(state, ignore_missing_defaults)

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

    def collect_dynamic_schema_entities(self, collector):
        for child_obj in self.non_gui_children.values():
            child_obj.collect_dynamic_schema_entities(collector)

        if self.is_dynamic_schema_node:
            collector.add_entity(self)

    def settings_value(self):
        if self._override_state is OverrideState.NOT_DEFINED:
            return NOT_SET

        if self._override_state is OverrideState.DEFAULTS:
            is_dynamic_schema_node = (
                self.is_dynamic_schema_node or self.is_in_dynamic_schema_node
            )
            output = {}
            for key, child_obj in self.non_gui_children.items():
                if child_obj.is_dynamic_schema_node:
                    continue

                child_value = child_obj.settings_value()
                if (
                    not is_dynamic_schema_node
                    and not child_obj.is_file
                    and not child_obj.file_item
                ):
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

        old_metadata = metadata.get(M_OVERRIDDEN_KEY)
        if old_metadata:
            old_metadata_set = set(old_metadata)
            new_metadata = []
            for key in self.non_gui_children.keys():
                if key in old_metadata:
                    new_metadata.append(key)
                    old_metadata_set.remove(key)

            for key in old_metadata_set:
                new_metadata.append(key)
            metadata[M_OVERRIDDEN_KEY] = new_metadata

        return value, metadata

    def update_default_value(self, value, log_invalid_types=True):
        """Update default values.

        Not an api method, should be called by parent.
        """

        self._default_log_invalid_types = log_invalid_types
        value = self._check_update_value(
            value, "default", log_invalid_types
        )
        self.has_default_value = value is not NOT_SET
        # TODO add value validation
        value, metadata = self._prepare_value(value)
        self._default_metadata = metadata

        if value is NOT_SET:
            for child_obj in self.non_gui_children.values():
                child_obj.update_default_value(value, log_invalid_types)
            return

        value_keys = set(value.keys())
        expected_keys = set(self.non_gui_children)
        unknown_keys = value_keys - expected_keys
        if unknown_keys and log_invalid_types:
            self.log.warning(
                "{} Unknown keys in default values: {}".format(
                    self.path,
                    ", ".join("\"{}\"".format(key) for key in unknown_keys)
                )
            )

        for key, child_obj in self.non_gui_children.items():
            child_value = value.get(key, NOT_SET)
            child_obj.update_default_value(child_value, log_invalid_types)

    def update_studio_value(self, value, log_invalid_types=True):
        """Update studio override values.

        Not an api method, should be called by parent.
        """

        self._studio_log_invalid_types = log_invalid_types
        value = self._check_update_value(
            value, "studio override", log_invalid_types
        )
        value, metadata = self._prepare_value(value)
        self._studio_override_metadata = metadata
        self.had_studio_override = metadata is not NOT_SET

        if value is NOT_SET:
            for child_obj in self.non_gui_children.values():
                child_obj.update_studio_value(value, log_invalid_types)
            return

        value_keys = set(value.keys())
        expected_keys = set(self.non_gui_children)
        unknown_keys = value_keys - expected_keys
        if unknown_keys and log_invalid_types:
            self.log.warning(
                "{} Unknown keys in studio overrides: {}".format(
                    self.path,
                    ", ".join("\"{}\"".format(key) for key in unknown_keys)
                )
            )
        for key, child_obj in self.non_gui_children.items():
            child_value = value.get(key, NOT_SET)
            child_obj.update_studio_value(child_value, log_invalid_types)

    def update_project_value(self, value, log_invalid_types=True):
        """Update project override values.

        Not an api method, should be called by parent.
        """

        self._project_log_invalid_types = log_invalid_types
        value = self._check_update_value(
            value, "project override", log_invalid_types
        )
        value, metadata = self._prepare_value(value)
        self._project_override_metadata = metadata
        self.had_project_override = metadata is not NOT_SET

        if value is NOT_SET:
            for child_obj in self.non_gui_children.values():
                child_obj.update_project_value(value, log_invalid_types)
            return

        value_keys = set(value.keys())
        expected_keys = set(self.non_gui_children)
        unknown_keys = value_keys - expected_keys
        if unknown_keys and log_invalid_types:
            self.log.warning(
                "{} Unknown keys in project overrides: {}".format(
                    self.path,
                    ", ".join("\"{}\"".format(key) for key in unknown_keys)
                )
            )

        for key, child_obj in self.non_gui_children.items():
            child_value = value.get(key, NOT_SET)
            child_obj.update_project_value(child_value, log_invalid_types)

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

        self._update_current_metadata()

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

        self._update_current_metadata()

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


class RootsDictEntity(DictImmutableKeysEntity):
    """Entity that adds ability to fill value for roots of current project.

    Value schema is defined by `object_type`.

    It is not possible to change override state (Studio values will always
    contain studio overrides and same for project). That is because roots can
    be totally different for each project.
    """
    _origin_schema_data = None
    schema_types = ["dict-roots"]

    def _item_initialization(self):
        origin_schema_data = self.schema_data

        self.separate_items = origin_schema_data.get("separate_items", True)
        object_type = origin_schema_data.get("object_type")
        if isinstance(object_type, STRING_TYPE):
            object_type = {"type": object_type}
        self.object_type = object_type

        if self.group_item is None and not self.is_group:
            self.is_group = True

        schema_data = copy.deepcopy(self.schema_data)
        schema_data["children"] = []

        self.schema_data = schema_data
        self._origin_schema_data = origin_schema_data

        self._default_value = NOT_SET
        self._studio_value = NOT_SET
        self._project_value = NOT_SET

        super(RootsDictEntity, self)._item_initialization()

    def schema_validations(self):
        if self.object_type is None:
            reason = (
                "Missing children definitions for root values"
                " ('object_type' not filled)."
            )
            raise EntitySchemaError(self, reason)

        if not isinstance(self.object_type, dict):
            reason = (
                "Children definitions for root values must be dictionary"
                " ('object_type' is \"{}\")."
            ).format(str(type(self.object_type)))
            raise EntitySchemaError(self, reason)

        super(RootsDictEntity, self).schema_validations()

    def set_override_state(self, state, ignore_missing_defaults):
        self.children = []
        self.non_gui_children = {}
        self.gui_layout = []

        roots_entity = self.get_entity_from_path(
            "project_anatomy/roots"
        )
        children = []
        first = True
        for key in roots_entity.keys():
            if first:
                first = False
            elif self.separate_items:
                children.append({"type": "separator"})
            child = copy.deepcopy(self.object_type)
            child["key"] = key
            child["label"] = key
            children.append(child)

        schema_data = copy.deepcopy(self.schema_data)
        schema_data["children"] = children

        self._add_children(schema_data)

        self._set_children_values(state, ignore_missing_defaults)

        super(RootsDictEntity, self).set_override_state(
            state, True
        )

        if state == OverrideState.STUDIO:
            self.add_to_studio_default()

        elif state == OverrideState.PROJECT:
            self.add_to_project_override()

    def on_child_change(self, child_obj):
        if self._override_state is OverrideState.STUDIO:
            if not child_obj.has_studio_override:
                self.add_to_studio_default()

        elif self._override_state is OverrideState.PROJECT:
            if not child_obj.has_project_override:
                self.add_to_project_override()

        return super(RootsDictEntity, self).on_child_change(child_obj)

    def _set_children_values(self, state, ignore_missing_defaults):
        if state >= OverrideState.DEFAULTS:
            default_value = self._default_value
            if default_value is NOT_SET:
                if (
                    not ignore_missing_defaults
                    and state > OverrideState.DEFAULTS
                ):
                    raise DefaultsNotDefined(self)
                else:
                    default_value = {}

            for key, child_obj in self.non_gui_children.items():
                child_value = default_value.get(key, NOT_SET)
                child_obj.update_default_value(child_value)

        if state >= OverrideState.STUDIO:
            value = self._studio_value
            if value is NOT_SET:
                value = {}

            for key, child_obj in self.non_gui_children.items():
                child_value = value.get(key, NOT_SET)
                child_obj.update_studio_value(child_value)

        if state >= OverrideState.PROJECT:
            value = self._project_value
            if value is NOT_SET:
                value = {}

            for key, child_obj in self.non_gui_children.items():
                child_value = value.get(key, NOT_SET)
                child_obj.update_project_value(child_value)

    def _update_current_metadata(self):
        """Override this method as this entity should not have metadata."""
        self._metadata_are_modified = False
        self._current_metadata = {}

    def update_default_value(self, value, log_invalid_types=True):
        """Update default values.

        Not an api method, should be called by parent.
        """

        self._default_log_invalid_types = log_invalid_types
        value = self._check_update_value(
            value, "default", log_invalid_types
        )
        value, _ = self._prepare_value(value)

        self._default_value = value
        self._default_metadata = {}
        self.has_default_value = value is not NOT_SET

    def update_studio_value(self, value, log_invalid_types=True):
        """Update studio override values.

        Not an api method, should be called by parent.
        """

        self._studio_log_invalid_types = log_invalid_types
        value = self._check_update_value(
            value, "studio override", log_invalid_types
        )
        value, _ = self._prepare_value(value)

        self._studio_value = value
        self._studio_override_metadata = {}
        self.had_studio_override = value is not NOT_SET

    def update_project_value(self, value, log_invalid_types=True):
        """Update project override values.

        Not an api method, should be called by parent.
        """

        self._project_log_invalid_types = log_invalid_types
        value = self._check_update_value(
            value, "project override", log_invalid_types
        )
        value, _metadata = self._prepare_value(value)

        self._project_value = value
        self._project_override_metadata = {}
        self.had_project_override = value is not NOT_SET


class SyncServerSites(DictImmutableKeysEntity):
    """Dictionary enity for sync sites.

    Can be used only in project settings.

    Is loading sites from system settings. Uses site name as key and by site's
    provider loads project settings schemas calling method
    `get_project_settings_schema` on provider.

    Each provider have `enabled` boolean entity to be able know if site should
    be enabled for the project. Enabled is by default set to False.
    """
    schema_types = ["sync-server-sites"]

    def _item_initialization(self):
        # Make sure this is a group
        if self.group_item is None and not self.is_group:
            self.is_group = True

        # Fake children for `dict` validations
        self.schema_data["children"] = []
        # Site names changed or were removed
        #   - to find out that site names was removed so project values
        #       contain more data than should
        self._sites_changed = False

        super(SyncServerSites, self)._item_initialization()

    def set_override_state(self, state, ignore_missing_defaults):
        # Cleanup children related attributes
        self.children = []
        self.non_gui_children = {}
        self.gui_layout = []

        # Create copy of schema
        schema_data = copy.deepcopy(self.schema_data)
        # Collect children
        children = self._get_children()
        schema_data["children"] = children

        self._add_children(schema_data)

        self._sites_changed = False
        self._set_children_values(state, ignore_missing_defaults)

        super(SyncServerSites, self).set_override_state(state, True)

    @property
    def has_unsaved_changes(self):
        if self._sites_changed:
            return True
        return super(SyncServerSites, self).has_unsaved_changes

    @property
    def has_studio_override(self):
        if self._sites_changed:
            return True
        return super(SyncServerSites, self).has_studio_override

    @property
    def has_project_override(self):
        if self._sites_changed:
            return True
        return super(SyncServerSites, self).has_project_override

    def _get_children(self):
        from openpype_modules import sync_server

        # Load system settings to find out all created sites
        modules_entity = self.get_entity_from_path("system_settings/modules")
        sync_server_settings_entity = modules_entity.get("sync_server")

        # Get project settings configurations for all providers
        project_settings_schema = (
            sync_server
            .SyncServerModule
            .get_project_settings_schema()
        )

        children = []
        # Add 'enabled' for each site to be able know if should be used for
        #   the project
        checkbox_child = {
            "type": "boolean",
            "key": "enabled",
            "default": False
        }
        if sync_server_settings_entity is not None:
            sites_entity = sync_server_settings_entity["sites"]
            for site_name, provider_entity in sites_entity.items():
                provider_name = provider_entity["provider"].value
                provider_children = copy.deepcopy(
                    project_settings_schema.get(provider_name)
                ) or []
                provider_children.insert(0, copy.deepcopy(checkbox_child))
                children.append({
                    "type": "dict",
                    "key": site_name,
                    "label": site_name,
                    "checkbox_key": "enabled",
                    "children": provider_children
                })

        return children

    def _set_children_values(self, state, ignore_missing_defaults):
        current_site_names = set(self.non_gui_children.keys())

        if state >= OverrideState.DEFAULTS:
            default_value = self._default_value
            if default_value is NOT_SET:
                if (
                    not ignore_missing_defaults
                    and state > OverrideState.DEFAULTS
                ):
                    raise DefaultsNotDefined(self)
                else:
                    default_value = {}

            for key, child_obj in self.non_gui_children.items():
                child_value = default_value.get(key, NOT_SET)
                child_obj.update_default_value(child_value)

        if state >= OverrideState.STUDIO:
            value = self._studio_value
            if value is NOT_SET:
                value = {}

            for key, child_obj in self.non_gui_children.items():
                child_value = value.get(key, NOT_SET)
                child_obj.update_studio_value(child_value)

            if state is OverrideState.STUDIO:
                value_keys = set(value.keys())
                self._sites_changed = value_keys != current_site_names

        if state >= OverrideState.PROJECT:
            value = self._project_value
            if value is NOT_SET:
                value = {}

            for key, child_obj in self.non_gui_children.items():
                child_value = value.get(key, NOT_SET)
                child_obj.update_project_value(child_value)

            if state is OverrideState.PROJECT:
                value_keys = set(value.keys())
                self._sites_changed = value_keys != current_site_names

    def _update_current_metadata(self):
        """Override this method as this entity should not have metadata."""
        self._metadata_are_modified = False
        self._current_metadata = {}

    def update_default_value(self, value, log_invalid_types=True):
        """Update default values.

        Not an api method, should be called by parent.
        """

        self._default_log_invalid_types = log_invalid_types
        value = self._check_update_value(
            value, "default", log_invalid_types
        )
        value, _ = self._prepare_value(value)

        self._default_value = value
        self._default_metadata = {}
        self.has_default_value = value is not NOT_SET

    def update_studio_value(self, value, log_invalid_types=True):
        """Update studio override values.

        Not an api method, should be called by parent.
        """

        self._studio_log_invalid_types = log_invalid_types
        value = self._check_update_value(
            value, "studio override", log_invalid_types
        )
        value, _ = self._prepare_value(value)

        self._studio_value = value
        self._studio_override_metadata = {}
        self.had_studio_override = value is not NOT_SET

    def update_project_value(self, value, log_invalid_types=True):
        """Update project override values.

        Not an api method, should be called by parent.
        """

        self._project_log_invalid_types = log_invalid_types
        value = self._check_update_value(
            value, "project override", log_invalid_types
        )
        value, _metadata = self._prepare_value(value)

        self._project_value = value
        self._project_override_metadata = {}
        self.had_project_override = value is not NOT_SET
