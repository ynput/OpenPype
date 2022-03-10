import copy

from .lib import (
    OverrideState,
    NOT_SET
)
from openpype.settings.constants import (
    METADATA_KEYS,
    M_OVERRIDDEN_KEY,
    KEY_REGEX
)
from . import (
    BaseItemEntity,
    ItemEntity,
    GUIEntity
)
from .exceptions import (
    SchemaDuplicatedKeys,
    EntitySchemaError,
    InvalidKeySymbols
)


class DictConditionalEntity(ItemEntity):
    """Entity represents dictionay with only one persistent key definition.

    The persistent key is enumerator which define rest of children under
    dictionary. There is not possibility of shared children.

    Entity's keys can't be removed or added. But they may change based on
    the persistent key. If you're change value manually (key by key) make sure
    you'll change value of the persistent key as first. It is recommended to
    use `set` method which handle this for you.

    It is possible to use entity similar way as `dict` object. Returned values
    are not real settings values but entities representing the value.
    """
    schema_types = ["dict-conditional"]
    _default_label_wrap = {
        "use_label_wrap": False,
        "collapsible": False,
        "collapsed": True
    }

    def __getitem__(self, key):
        """Return entity inder key."""
        if key == self.enum_key:
            return self.enum_entity
        return self.non_gui_children[self.current_enum][key]

    def __setitem__(self, key, value):
        """Set value of item under key."""
        if key == self.enum_key:
            child_obj = self.enum_entity
        else:
            child_obj = self.non_gui_children[self.current_enum][key]
        child_obj.set(value)

    def __iter__(self):
        """Iter through keys."""
        for key in self.keys():
            yield key

    def __contains__(self, key):
        """Check if key is available."""
        if key == self.enum_key:
            return True
        return key in self.non_gui_children[self.current_enum]

    def get(self, key, default=None):
        """Safe entity getter by key."""
        if key == self.enum_key:
            return self.enum_entity
        return self.non_gui_children[self.current_enum].get(key, default)

    def keys(self):
        """Entity's keys."""
        keys = list(self.non_gui_children[self.current_enum].keys())
        keys.insert(0, [self.enum_key])
        return keys

    def values(self):
        """Children entities."""
        values = [
            self.enum_entity
        ]
        for child_entiy in self.non_gui_children[self.current_enum].values():
            values.append(child_entiy)
        return values

    def items(self):
        """Children entities paired with their key (key, value)."""
        items = [
            (self.enum_key, self.enum_entity)
        ]
        for key, value in self.non_gui_children[self.current_enum].items():
            items.append((key, value))
        return items

    def set(self, value):
        """Set value."""
        new_value = self.convert_to_valid_type(value)
        # First change value of enum key if available
        if self.enum_key in new_value:
            self.enum_entity.set(new_value.pop(self.enum_key))

        for _key, _value in new_value.items():
            self.non_gui_children[self.current_enum][_key].set(_value)

    def has_child_with_key(self, key):
        return key in self.keys()

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

        # Entity must be group or in group
        if (
            self.group_item is None
            and not self.is_dynamic_item
            and not self.is_in_dynamic_item
        ):
            self.is_group = True

        # Children are stored by key as keys are immutable and are defined by
        # schema
        self.valid_value_types = (dict, )
        self.children = {}
        self.non_gui_children = {}
        self.gui_layout = {}

        if self.is_dynamic_item:
            self.require_key = False

        self.enum_key = self.schema_data.get("enum_key")
        self.enum_label = self.schema_data.get("enum_label")
        self.enum_children = self.schema_data.get("enum_children")
        self.enum_default = self.schema_data.get("enum_default")

        self.enum_entity = None

        # GUI attributes
        self.enum_is_horizontal = self.schema_data.get(
            "enum_is_horizontal", False
        )
        # `enum_on_right` can be used only if
        self.enum_on_right = self.schema_data.get("enum_on_right", False)

        self.highlight_content = self.schema_data.get(
            "highlight_content", False
        )
        self.show_borders = self.schema_data.get("show_borders", True)

        self._add_children()

    @property
    def current_enum(self):
        """Current value of enum entity.

        This value define what children are used.
        """
        if self.enum_entity is None:
            return None
        return self.enum_entity.value

    def schema_validations(self):
        """Validation of schema data."""
        # Enum key must be defined
        if self.enum_key is None:
            raise EntitySchemaError(self, "Key 'enum_key' is not set.")

        # Validate type of enum children
        if not isinstance(self.enum_children, list):
            raise EntitySchemaError(
                self, "Key 'enum_children' must be a list. Got: {}".format(
                    str(type(self.enum_children))
                )
            )

        # Without defined enum children entity has nothing to do
        if not self.enum_children:
            raise EntitySchemaError(self, (
                "Key 'enum_children' have empty value. Entity can't work"
                " without children definitions."
            ))

        children_def_keys = []
        for children_def in self.enum_children:
            if not isinstance(children_def, dict):
                raise EntitySchemaError(self, (
                    "Children definition under key 'enum_children' must"
                    " be a dictionary."
                ))

            if "key" not in children_def:
                raise EntitySchemaError(self, (
                    "Children definition under key 'enum_children' miss"
                    " 'key' definition."
                ))
            # We don't validate regex of these keys because they will be stored
            #   as value at the end.
            key = children_def["key"]
            if key in children_def_keys:
                # TODO this hould probably be different exception?
                raise SchemaDuplicatedKeys(self, key)
            children_def_keys.append(key)

        # Validate key duplications per each enum item
        for children in self.children.values():
            children_keys = set()
            children_keys.add(self.enum_key)
            for child_entity in children:
                if not isinstance(child_entity, BaseItemEntity):
                    continue
                elif child_entity.key not in children_keys:
                    children_keys.add(child_entity.key)
                else:
                    raise SchemaDuplicatedKeys(self, child_entity.key)

        # Enum key must match key regex
        if not KEY_REGEX.match(self.enum_key):
            raise InvalidKeySymbols(self.path, self.enum_key)

        # Validate all remaining keys with key regex
        for children_by_key in self.non_gui_children.values():
            for key in children_by_key.keys():
                if not KEY_REGEX.match(key):
                    raise InvalidKeySymbols(self.path, key)

        super(DictConditionalEntity, self).schema_validations()
        # Trigger schema validation on children entities
        for children in self.children.values():
            for child_obj in children:
                child_obj.schema_validations()

    def on_change(self):
        """Update metadata on change and pass change to parent."""
        self._update_current_metadata()

        for callback in self.on_change_callbacks:
            callback()
        self.parent.on_child_change(self)

    def on_child_change(self, child_obj):
        """Trigger on change callback if child changes are not ignored."""
        if self._ignore_child_changes:
            return

        if (
            child_obj is self.enum_entity
            or child_obj in self.children[self.current_enum]
        ):
            self.on_change()

    def _add_children(self):
        """Add children from schema data and repare enum items.

        Each enum item must have defined it's children. None are shared across
        all enum items.

        Nice to have: Have ability to have shared keys across all enum items.

        All children are stored by their enum item.
        """
        # Skip if are not defined
        # - schema validations should raise and exception
        if not self.enum_children or not self.enum_key:
            return

        valid_enum_items = []
        for item in self.enum_children:
            if isinstance(item, dict) and "key" in item:
                valid_enum_items.append(item)

        enum_keys = []
        enum_items = []
        for item in valid_enum_items:
            item_key = item["key"]
            enum_keys.append(item_key)
            item_label = item.get("label") or item_key
            enum_items.append({item_key: item_label})

        if not enum_items:
            return

        if self.enum_default in enum_keys:
            default_key = self.enum_default
        else:
            default_key = enum_keys[0]

        # Create Enum child first
        enum_key = self.enum_key or "invalid"
        enum_schema = {
            "type": "enum",
            "multiselection": False,
            "enum_items": enum_items,
            "key": enum_key,
            "label": self.enum_label,
            "default": default_key
        }

        enum_entity = self.create_schema_object(enum_schema, self)
        self.enum_entity = enum_entity

        # Create children per each enum item
        for item in valid_enum_items:
            item_key = item["key"]
            # Make sure all keys have set value in these variables
            # - key 'children' is optional
            self.non_gui_children[item_key] = {}
            self.children[item_key] = []
            self.gui_layout[item_key] = []

            children = item.get("children") or []
            for children_schema in children:
                child_obj = self.create_schema_object(children_schema, self)
                self.children[item_key].append(child_obj)
                self.gui_layout[item_key].append(child_obj)
                if isinstance(child_obj, GUIEntity):
                    continue

                self.non_gui_children[item_key][child_obj.key] = child_obj

    def collect_static_entities_by_path(self):
        if self.is_dynamic_item or self.is_in_dynamic_item:
            return {}
        return {self.path: self}

    def get_child_path(self, child_obj):
        """Get hierarchical path of child entity.

        Child must be entity's direct children. This must be possible to get
        for any children even if not from current enum value.
        """
        if child_obj is self.enum_entity:
            return "/".join([self.path, self.enum_key])

        result_key = None
        for children in self.non_gui_children.values():
            for key, _child_obj in children.items():
                if _child_obj is child_obj:
                    result_key = key
                    break

        if result_key is None:
            raise ValueError("Didn't found child {}".format(child_obj))

        return "/".join([self.path, result_key])

    def _update_current_metadata(self):
        current_metadata = {}
        for key, child_obj in self.non_gui_children[self.current_enum].items():
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

        # Set override state on enum entity first
        self.enum_entity.set_override_state(state, ignore_missing_defaults)

        # Set override state on other enum children
        # - these must not raise exception about missing defaults
        for children_by_key in self.non_gui_children.values():
            for child_obj in children_by_key.values():
                child_obj.set_override_state(state, True)

        self._update_current_metadata()

    @property
    def value(self):
        output = {
            self.enum_key: self.enum_entity.value
        }
        for key, child_obj in self.non_gui_children[self.current_enum].items():
            output[key] = child_obj.value
        return output

    @property
    def has_unsaved_changes(self):
        if self._metadata_are_modified:
            return True

        return self._child_has_unsaved_changes

    @property
    def _child_has_unsaved_changes(self):
        if self.enum_entity.has_unsaved_changes:
            return True

        for child_obj in self.non_gui_children[self.current_enum].values():
            if child_obj.has_unsaved_changes:
                return True
        return False

    @property
    def has_studio_override(self):
        return self._child_has_studio_override

    @property
    def _child_has_studio_override(self):
        if self._override_state >= OverrideState.STUDIO:
            if self.enum_entity.has_studio_override:
                return True

            for child_obj in self.non_gui_children[self.current_enum].values():
                if child_obj.has_studio_override:
                    return True
        return False

    @property
    def has_project_override(self):
        return self._child_has_project_override

    @property
    def _child_has_project_override(self):
        if self._override_state >= OverrideState.PROJECT:
            if self.enum_entity.has_project_override:
                return True

            for child_obj in self.non_gui_children[self.current_enum].values():
                if child_obj.has_project_override:
                    return True
        return False

    def collect_dynamic_schema_entities(self, collector):
        if self.is_dynamic_schema_node:
            collector.add_entity(self)

    def settings_value(self):
        if self._override_state is OverrideState.NOT_DEFINED:
            return NOT_SET

        if self._override_state is OverrideState.DEFAULTS:
            children_items = [
                (self.enum_key, self.enum_entity)
            ]
            for item in self.non_gui_children[self.current_enum].items():
                children_items.append(item)

            output = {}
            for key, child_obj in children_items:
                output[key] = child_obj.settings_value()
            return output

        if self.is_group:
            if self._override_state is OverrideState.STUDIO:
                if not self.has_studio_override:
                    return NOT_SET
            elif self._override_state is OverrideState.PROJECT:
                if not self.has_project_override:
                    return NOT_SET

        output = {}
        children_items = [
            (self.enum_key, self.enum_entity)
        ]
        for item in self.non_gui_children[self.current_enum].items():
            children_items.append(item)

        for key, child_obj in children_items:
            value = child_obj.settings_value()
            if value is not NOT_SET:
                output[key] = value

        if not output:
            return NOT_SET

        output.update(self._current_metadata)
        return output

    def _prepare_value(self, value):
        if value is NOT_SET or self.enum_key not in value:
            return NOT_SET, NOT_SET

        enum_value = value.get(self.enum_key)
        if enum_value not in self.non_gui_children:
            return NOT_SET, NOT_SET

        # Create copy of value before poping values
        value = copy.deepcopy(value)
        metadata = {}
        for key in METADATA_KEYS:
            if key in value:
                metadata[key] = value.pop(key)

        enum_value = value.get(self.enum_key)

        old_metadata = metadata.get(M_OVERRIDDEN_KEY)
        if old_metadata:
            old_metadata_set = set(old_metadata)
            new_metadata = []
            non_gui_children = self.non_gui_children[enum_value]
            for key in non_gui_children.keys():
                if key in old_metadata:
                    new_metadata.append(key)
                    old_metadata_set.remove(key)

            for key in old_metadata_set:
                new_metadata.append(key)
            metadata[M_OVERRIDDEN_KEY] = new_metadata

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
            self.enum_entity.update_default_value(value)
            for children_by_key in self.non_gui_children.values():
                for child_obj in children_by_key.values():
                    child_obj.update_default_value(value)
            return

        value_keys = set(value.keys())
        enum_value = value[self.enum_key]
        expected_keys = set(self.non_gui_children[enum_value].keys())
        expected_keys.add(self.enum_key)
        unknown_keys = value_keys - expected_keys
        if unknown_keys:
            self.log.warning(
                "{} Unknown keys in default values: {}".format(
                    self.path,
                    ", ".join("\"{}\"".format(key) for key in unknown_keys)
                )
            )

        self.enum_entity.update_default_value(enum_value)
        for children_by_key in self.non_gui_children.values():
            value_copy = copy.deepcopy(value)
            for key, child_obj in children_by_key.items():
                child_value = value_copy.get(key, NOT_SET)
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
            self.enum_entity.update_studio_value(value)
            for children_by_key in self.non_gui_children.values():
                for child_obj in children_by_key.values():
                    child_obj.update_studio_value(value)
            return

        value_keys = set(value.keys())
        enum_value = value[self.enum_key]
        expected_keys = set(self.non_gui_children[enum_value])
        expected_keys.add(self.enum_key)
        unknown_keys = value_keys - expected_keys
        if unknown_keys:
            self.log.warning(
                "{} Unknown keys in studio overrides: {}".format(
                    self.path,
                    ", ".join("\"{}\"".format(key) for key in unknown_keys)
                )
            )

        self.enum_entity.update_studio_value(enum_value)
        for children_by_key in self.non_gui_children.values():
            value_copy = copy.deepcopy(value)
            for key, child_obj in children_by_key.items():
                child_value = value_copy.get(key, NOT_SET)
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
            self.enum_entity.update_project_value(value)
            for children_by_key in self.non_gui_children.values():
                for child_obj in children_by_key.values():
                    child_obj.update_project_value(value)
            return

        value_keys = set(value.keys())
        enum_value = value[self.enum_key]
        expected_keys = set(self.non_gui_children[enum_value])
        expected_keys.add(self.enum_key)
        unknown_keys = value_keys - expected_keys
        if unknown_keys:
            self.log.warning(
                "{} Unknown keys in project overrides: {}".format(
                    self.path,
                    ", ".join("\"{}\"".format(key) for key in unknown_keys)
                )
            )

        self.enum_entity.update_project_value(enum_value)
        for children_by_key in self.non_gui_children.values():
            value_copy = copy.deepcopy(value)
            for key, child_obj in children_by_key.items():
                child_value = value_copy.get(key, NOT_SET)
                child_obj.update_project_value(child_value)

    def _discard_changes(self, on_change_trigger):
        self._ignore_child_changes = True

        self.enum_entity.discard_changes(on_change_trigger)
        for children_by_key in self.non_gui_children.values():
            for child_obj in children_by_key.values():
                child_obj.discard_changes(on_change_trigger)

        self._ignore_child_changes = False

    def _add_to_studio_default(self, on_change_trigger):
        self._ignore_child_changes = True

        self.enum_entity.add_to_studio_default(on_change_trigger)
        for children_by_key in self.non_gui_children.values():
            for child_obj in children_by_key.values():
                child_obj.add_to_studio_default(on_change_trigger)

        self._ignore_child_changes = False

        self._update_current_metadata()

        self.parent.on_child_change(self)

    def _remove_from_studio_default(self, on_change_trigger):
        self._ignore_child_changes = True

        self.enum_entity.remove_from_studio_default(on_change_trigger)
        for children_by_key in self.non_gui_children.values():
            for child_obj in children_by_key.values():
                child_obj.remove_from_studio_default(on_change_trigger)

        self._ignore_child_changes = False

    def _add_to_project_override(self, on_change_trigger):
        self._ignore_child_changes = True

        self.enum_entity.add_to_project_override(on_change_trigger)
        for children_by_key in self.non_gui_children.values():
            for child_obj in children_by_key.values():
                child_obj.add_to_project_override(on_change_trigger)

        self._ignore_child_changes = False

        self._update_current_metadata()

        self.parent.on_child_change(self)

    def _remove_from_project_override(self, on_change_trigger):
        if self._override_state is not OverrideState.PROJECT:
            return

        self._ignore_child_changes = True

        self.enum_entity.remove_from_project_override(on_change_trigger)
        for children_by_key in self.non_gui_children.values():
            for child_obj in children_by_key.values():
                child_obj.remove_from_project_override(on_change_trigger)

        self._ignore_child_changes = False

    def reset_callbacks(self):
        """Reset registered callbacks on entity and children."""
        super(DictConditionalEntity, self).reset_callbacks()
        for children in self.children.values():
            for child_entity in children:
                child_entity.reset_callbacks()


class SyncServerProviders(DictConditionalEntity):
    schema_types = ["sync-server-providers"]

    def _add_children(self):
        self.enum_key = "provider"
        self.enum_label = "Provider"

        enum_children = self._get_enum_children()
        if not enum_children:
            enum_children.append({
                "key": None,
                "label": "< Nothing >"
            })
        self.enum_children = enum_children

        super(SyncServerProviders, self)._add_children()

    def _get_enum_children(self):
        from openpype_modules import sync_server

        from openpype_modules.sync_server.providers import lib as lib_providers

        provider_code_to_label = {}
        providers = lib_providers.factory.providers
        for provider_code, provider_info in providers.items():
            provider, _ = provider_info
            provider_code_to_label[provider_code] = provider.LABEL

        system_settings_schema = (
            sync_server
            .SyncServerModule
            .get_system_settings_schema()
        )

        enum_children = []
        for provider_code, configurables in system_settings_schema.items():
            # any site could be exposed or vendorized by different site
            # eg studio site content could be mapped on sftp site, single file
            # accessible via 2 different protocols (sites)
            configurables.append(
                {
                    "type": "list",
                    "key": "alternative_sites",
                    "label": "Alternative sites",
                    "object_type": "text"
                }
            )
            label = provider_code_to_label.get(provider_code) or provider_code

            enum_children.append({
                "key": provider_code,
                "label": label,
                "children": configurables
            })
        return enum_children
