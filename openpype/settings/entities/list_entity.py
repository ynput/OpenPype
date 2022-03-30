import copy
import six
import re
from . import (
    BaseEntity,
    EndpointEntity
)
from .lib import (
    NOT_SET,
    OverrideState
)
from .exceptions import (
    DefaultsNotDefined,
    StudioDefaultsNotDefined,
    EntitySchemaError
)


class ListEntity(EndpointEntity):
    schema_types = ["list"]
    _default_label_wrap = {
        "use_label_wrap": False,
        "collapsible": True,
        "collapsed": False
    }
    _key_regex = re.compile(r"[0-9]+")

    def __iter__(self):
        for item in self.children:
            yield item

    def __bool__(self):
        """Returns true because len may return 0."""
        return True

    def __len__(self):
        return len(self.children)

    def __contains__(self, item):
        if isinstance(item, BaseEntity):
            for child_entity in self.children:
                if child_entity.id == item.id:
                    return True
            return False

        for _item in self.value:
            if item == _item:
                return True
        return False

    def __getitem__(self, idx):
        if not isinstance(idx, int):
            idx = int(idx)
        return self.children[idx]

    def __setitem__(self, idx, value):
        if not isinstance(idx, int):
            idx = int(idx)
        self.children[idx].set(value)

    def get(self, idx, default=None):
        if not isinstance(idx, int):
            idx = int(idx)

        if idx < len(self.children):
            return self.children[idx]
        return default

    def index(self, item):
        if isinstance(item, BaseEntity):
            for idx, child_entity in enumerate(self.children):
                if child_entity.id == item.id:
                    return idx
        else:
            for idx, _item in enumerate(self.value):
                if item == _item:
                    return idx
        raise ValueError(
            "{} is not in {}".format(item, self.__class__.__name__)
        )

    def append(self, item):
        child_obj = self.add_new_item(trigger_change=False)
        child_obj.set(item)
        self.on_child_change(child_obj)

    def extend(self, items):
        for item in items:
            self.append(item)

    def clear(self):
        if not self.children:
            return

        first_item = self.children.pop(0)
        while self.children:
            self.children.pop(0)
        self.on_child_change(first_item)

    def pop(self, idx):
        item = self.children.pop(idx)
        self.on_child_change(item)
        return item

    def remove(self, item):
        try:
            self.pop(self.index(item))
        except ValueError:
            raise ValueError("ListEntity.remove(x): x not in ListEntity")

    def insert(self, idx, item):
        child_obj = self.add_new_item(idx, trigger_change=False)
        child_obj.set(item)
        self.on_child_change(child_obj)

    def _add_new_item(self, idx=None):
        child_obj = self.create_schema_object(self.item_schema, self, True)
        if idx is None:
            self.children.append(child_obj)
        else:
            self.children.insert(idx, child_obj)
        return child_obj

    def add_new_item(self, idx=None, trigger_change=True):
        child_obj = self._add_new_item(idx)
        child_obj.set_override_state(
            self._override_state, self._ignore_missing_defaults
        )

        if trigger_change:
            self.on_child_change(child_obj)
        return child_obj

    def swap_items(self, item_1, item_2):
        index_1 = self.index(item_1)
        index_2 = self.index(item_2)
        self.swap_indexes(index_1, index_2)

    def swap_indexes(self, index_1, index_2):
        children_len = len(self.children)
        if index_1 > children_len or index_2 > children_len:
            raise IndexError(
                "{} index out of range".format(self.__class__.__name__)
            )
        self.children[index_1], self.children[index_2] = (
            self.children[index_2], self.children[index_1]
        )
        self.on_change()

    def has_child_with_key(self, key):
        if (
            key
            and isinstance(key, six.string_types)
            and self._key_regex.match(key)
        ):
            key = int(key)

        if not isinstance(key, int):
            return False

        return 0 <= key < len(self.children)

    def _convert_to_valid_type(self, value):
        if isinstance(value, (set, tuple)):
            return list(value)
        return NOT_SET

    def _item_initialization(self):
        self.valid_value_types = (list, )
        self.children = []
        self.value_on_not_set = []

        self._ignore_child_changes = False

        item_schema = self.schema_data["object_type"]
        if not isinstance(item_schema, dict):
            item_schema = {"type": item_schema}

        obj_template_name = self.schema_hub.get_template_name(item_schema)
        _item_schemas = self.schema_hub.resolve_schema_data(item_schema)
        if len(_item_schemas) == 1:
            self.item_schema = _item_schemas[0]
            if self.item_schema != item_schema:
                if "label" in self.item_schema:
                    self.item_schema.pop("label")
                self.item_schema["use_label_wrap"] = False
        else:
            self.item_schema = _item_schemas

        # Store if was used template or schema
        self._obj_template_name = obj_template_name

        if self.group_item is None:
            self.is_group = True

        # Value that was set on set_override_state
        self.initial_value = []

    def schema_validations(self):
        if isinstance(self.item_schema, list):
            reason = (
                "`ListWidget` has multiple items as object type."
            )
            raise EntitySchemaError(self, reason)

        super(ListEntity, self).schema_validations()

        if self.is_dynamic_item and self.use_label_wrap:
            reason = (
                "`ListWidget` can't have set `use_label_wrap` to True and"
                " be used as widget at the same time."
            )
            raise EntitySchemaError(self, reason)

        if self.use_label_wrap and not self.label:
            reason = (
                "`ListWidget` can't have set `use_label_wrap` to True and"
                " not have set \"label\" key at the same time."
            )
            raise EntitySchemaError(self, reason)

        # Validate object type schema
        validate_children = True
        for child_entity in self.children:
            child_entity.schema_validations()
            validate_children = False
            break

        if validate_children and self._obj_template_name:
            _validated = self.schema_hub.is_dynamic_template_validated(
                self._obj_template_name
            )
            _validating = self.schema_hub.is_dynamic_template_validating(
                self._obj_template_name
            )
            validate_children = not _validated and not _validating

        if not validate_children:
            return

        def _validate():
            idx = 0
            tmp_child = self._add_new_item(idx)
            tmp_child.schema_validations()
            self.children.pop(idx)

        if self._obj_template_name:
            with self.schema_hub.validating_dynamic(self._obj_template_name):
                _validate()
        else:
            _validate()

    def get_child_path(self, child_obj):
        result_idx = None
        for idx, _child_obj in enumerate(self.children):
            if _child_obj is child_obj:
                result_idx = idx
                break

        if result_idx is None:
            raise ValueError("Didn't found child {}".format(child_obj))

        return "/".join([self.path, str(result_idx)])

    def set(self, value):
        new_value = self.convert_to_valid_type(value)
        self.clear()
        for item in new_value:
            self.append(item)

    def on_child_change(self, _child_entity):
        if self._ignore_child_changes:
            return

        if self._override_state is OverrideState.STUDIO:
            self._has_studio_override = True
        elif self._override_state is OverrideState.PROJECT:
            self._has_project_override = True
        self.on_change()

    def set_override_state(self, state, ignore_missing_defaults):
        # Trigger override state change of root if is not same
        if self.root_item.override_state is not state:
            self.root_item.set_override_state(state)
            return

        self._override_state = state
        self._ignore_missing_defaults = ignore_missing_defaults

        while self.children:
            self.children.pop(0)

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

        value = NOT_SET
        if self._override_state is OverrideState.PROJECT:
            if self.had_project_override:
                value = self._project_override_value
            self._has_project_override = self.had_project_override

        if value is NOT_SET or self._override_state is OverrideState.STUDIO:
            if self.had_studio_override:
                value = self._studio_override_value
            self._has_studio_override = self.had_studio_override

        if value is NOT_SET or self._override_state is OverrideState.DEFAULTS:
            if self.has_default_value:
                value = self._default_value
            else:
                value = self.value_on_not_set

        for item in value:
            child_obj = self._add_new_item()
            child_obj.update_default_value(
                item, self._default_log_invalid_types
            )
            if self._override_state is OverrideState.PROJECT:
                if self.had_project_override:
                    child_obj.update_project_value(
                        item, self._project_log_invalid_types
                    )
                elif self.had_studio_override:
                    child_obj.update_studio_value(
                        item, self._studio_log_invalid_types
                    )

            elif self._override_state is OverrideState.STUDIO:
                if self.had_studio_override:
                    child_obj.update_studio_value(
                        item, self._studio_log_invalid_types
                    )

        for child_obj in self.children:
            child_obj.set_override_state(
                self._override_state, ignore_missing_defaults
            )

        self.initial_value = self.settings_value()

    @property
    def value(self):
        output = []
        for child_obj in self.children:
            output.append(child_obj.value)
        return output

    @property
    def has_unsaved_changes(self):
        if self._override_state is OverrideState.NOT_DEFINED:
            return False

        if self._override_state is OverrideState.DEFAULTS:
            if not self.has_default_value:
                return True

        elif self._override_state is OverrideState.STUDIO:
            if self.had_studio_override != self._has_studio_override:
                return True

            if not self._has_studio_override and not self.has_default_value:
                return True

        elif self._override_state is OverrideState.PROJECT:
            if self.had_project_override != self._has_project_override:
                return True

            if (
                not self._has_project_override
                and not self._has_studio_override
                and not self.has_default_value
            ):
                return True

        if self._child_has_unsaved_changes:
            return True

        if self.settings_value() != self.initial_value:
            return True
        return False

    @property
    def has_studio_override(self):
        if self._override_state >= OverrideState.STUDIO:
            return (
                self._has_studio_override
                or self._child_has_studio_override
            )
        return False

    @property
    def has_project_override(self):
        if self._override_state >= OverrideState.PROJECT:
            return (
                self._has_project_override
                or self._child_has_project_override
            )
        return False

    @property
    def _child_has_unsaved_changes(self):
        for child_obj in self.children:
            if child_obj.has_unsaved_changes:
                return True
        return False

    @property
    def _child_has_studio_override(self):
        if self._override_state >= OverrideState.STUDIO:
            for child_obj in self.children:
                if child_obj.has_studio_override:
                    return True
        return False

    @property
    def _child_has_project_override(self):
        if self._override_state is OverrideState.PROJECT:
            for child_obj in self.children:
                if child_obj.has_project_override:
                    return True
        return False

    def _settings_value(self):
        output = []
        for child_obj in self.children:
            output.append(child_obj.settings_value())
        return output

    def _discard_changes(self, on_change_trigger):
        if not self._can_discard_changes:
            return

        not_set = object()
        value = not_set
        if (
            self._override_state >= OverrideState.PROJECT
            and self.had_project_override
        ):
            value = copy.deepcopy(self._project_override_value)

        if (
            value is not_set
            and self._override_state >= OverrideState.STUDIO
            and self.had_studio_override
        ):
            value = copy.deepcopy(self._studio_override_value)

        if value is not_set and self._override_state >= OverrideState.DEFAULTS:
            if self.has_default_value:
                value = copy.deepcopy(self._default_value)
            else:
                value = copy.deepcopy(self.value_on_not_set)

        if value is not_set:
            raise NotImplementedError("BUG: Unexcpected part of code.")

        self._ignore_child_changes = True

        while self.children:
            self.children.pop(0)

        for item in value:
            child_obj = self._add_new_item()
            child_obj.update_default_value(
                item, self._default_log_invalid_types
            )
            if self._override_state is OverrideState.PROJECT:
                if self.had_project_override:
                    child_obj.update_project_value(
                        item, self._project_log_invalid_types
                    )
                elif self.had_studio_override:
                    child_obj.update_studio_value(
                        item, self._studio_log_invalid_types
                    )

            elif self._override_state is OverrideState.STUDIO:
                if self.had_studio_override:
                    child_obj.update_studio_value(
                        item, self._studio_log_invalid_types
                    )

            child_obj.set_override_state(
                self._override_state, self._ignore_missing_defaults
            )

        if self._override_state >= OverrideState.PROJECT:
            self._has_project_override = self.had_project_override

        if self._override_state >= OverrideState.STUDIO:
            self._has_studio_override = self.had_studio_override

        self._ignore_child_changes = False

        on_change_trigger.append(self.on_change)

    def _add_to_studio_default(self, _on_change_trigger):
        self._has_studio_override = True
        self.on_change()

    def _remove_from_studio_default(self, on_change_trigger):
        if not self._can_remove_from_studio_default:
            return

        value = self._default_value
        if value is NOT_SET:
            value = self.value_on_not_set

        self._ignore_child_changes = True

        while self.children:
            self.children.pop(0)

        for item in value:
            child_obj = self._add_new_item()
            child_obj.update_default_value(item)
            child_obj.set_override_state(
                self._override_state, self._ignore_missing_defaults
            )

        self._ignore_child_changes = False

        self._has_studio_override = False

        on_change_trigger.append(self.on_change)

    def _add_to_project_override(self, _on_change_trigger):
        self._has_project_override = True
        self.on_change()

    def _remove_from_project_override(self, on_change_trigger):
        if not self._can_remove_from_project_override:
            return

        if self._has_studio_override:
            value = self._studio_override_value
        elif self.has_default_value:
            value = self._default_value
        else:
            value = self.value_on_not_set

        self._ignore_child_changes = True

        while self.children:
            self.children.pop(0)

        for item in value:
            child_obj = self._add_new_item()
            child_obj.update_default_value(item)
            if self._has_studio_override:
                child_obj.update_studio_value(item)
            child_obj.set_override_state(
                self._override_state,
                self._ignore_missing_defaults
            )

        self._ignore_child_changes = False

        self._has_project_override = False

        on_change_trigger.append(self.on_change)

    def reset_callbacks(self):
        super(ListEntity, self).reset_callbacks()
        for child_entity in self.children:
            child_entity.reset_callbacks()
