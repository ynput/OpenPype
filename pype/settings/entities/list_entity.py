import copy
from . import (
    BaseEntity,
    EndpointEntity
)
from .lib import (
    NOT_SET,
    OverrideState
)
from .exceptions import DefaultsNotDefined


class ListEntity(EndpointEntity):
    schema_types = ["list"]

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

    def append(self, item):
        child_obj = self._add_new_item()
        child_obj.set_override_state(self._override_state)
        child_obj.set(item)
        self.on_change()

    def extend(self, items):
        for item in items:
            self.append(item)

    def clear(self):
        self.children.clear()
        self.on_change()

    def pop(self, idx):
        item = self.children.pop(idx)
        self.on_change()
        return item

    def remove(self, item):
        for idx, child_obj in enumerate(self.children):
            found = False
            if isinstance(item, BaseEntity):
                if child_obj is item:
                    found = True
            elif child_obj.value == item:
                found = True

            if found:
                self.pop(idx)
                return
        raise ValueError("ListEntity.remove(x): x not in ListEntity")

    def insert(self, idx, item):
        child_obj = self._add_new_item(idx)
        child_obj.set_override_state(self._override_state)
        child_obj.set(item)
        self.on_change()

    def _add_new_item(self, idx=None):
        child_obj = self.create_schema_object(self.item_schema, self, True)
        if idx is None:
            self.children.append(child_obj)
        else:
            self.children.insert(idx, child_obj)
        return child_obj

    def add_new_item(self, idx=None):
        child_obj = self._add_new_item(idx)
        child_obj.set_override_state(self._override_state)
        self.on_change()
        return child_obj

    def _item_initalization(self):
        self.valid_value_types = (list, )
        self.children = []
        self.value_on_not_set = []

        self._ignore_child_changes = False

        item_schema = self.schema_data["object_type"]
        if not isinstance(item_schema, dict):
            item_schema = {"type": item_schema}
        self.item_schema = item_schema

        if not self.group_item:
            self.is_group = True

        # Value that was set on set_override_state
        self.initial_value = []

        # GUI attributes
        self.use_label_wrap = self.schema_data.get("use_label_wrap") or False
        # Used only if `use_label_wrap` is set to True
        self.collapsible = self.schema_data.get("collapsible") or True
        self.collapsed = self.schema_data.get("collapsed") or False

    def schema_validations(self):
        super(ListEntity, self).schema_validations()

        if self.is_dynamic_item and self.use_label_wrap:
            raise ValueError(
                "`ListWidget` can't have set `use_label_wrap` to True and"
                " be used as widget at the same time."
            )

        if self.use_label_wrap and not self.label:
            raise ValueError(
                "`ListWidget` can't have set `use_label_wrap` to True and"
                " not have set \"label\" key at the same time."
            )

        for child_obj in self.children:
            child_obj.schema_validations()

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
        self._validate_value_type(value)
        self.clear()
        for item in value:
            self.append(item)

    def on_change(self):
        for callback in self.on_change_callbacks:
            callback()
        self.parent.on_child_change(self)

    def on_child_change(self, child_obj):
        if self._ignore_child_changes:
            return

        # TODO is this enough?
        if self._override_state is OverrideState.STUDIO:
            self._has_studio_override = self._child_has_studio_override
        elif self._override_state is OverrideState.PROJECT:
            self._has_project_override = self._child_has_project_override
        self.on_change()

    def set_override_state(self, state):
        # Trigger override state change of root if is not same
        if self.root_item.override_state is not state:
            self.root_item.set_override_state(state)
            return

        self._override_state = state

        while self.children:
            self.children.pop(0)

        if not self.has_default_value and state > OverrideState.DEFAULTS:
            # Ignore if is dynamic item and use default in that case
            if not self.is_dynamic_item and not self.is_in_dynamic_item:
                raise DefaultsNotDefined(self)

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
            child_obj.update_default_value(item)
            if self._override_state is OverrideState.PROJECT:
                if self.had_project_override:
                    child_obj.update_project_values(item)
                elif self.had_studio_override:
                    child_obj.update_studio_values(item)

            elif self._override_state is OverrideState.STUDIO:
                if self.had_studio_override:
                    child_obj.update_studio_values(item)

        for child_obj in self.children:
            child_obj.set_override_state(self._override_state)

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
        if self._override_state is OverrideState.NOT_DEFINED:
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
            child_obj.update_default_value(item)
            if self._override_state is OverrideState.PROJECT:
                if self.had_project_override:
                    child_obj.update_project_values(item)
                elif self.had_studio_override:
                    child_obj.update_studio_values(item)

            elif self._override_state is OverrideState.STUDIO:
                if self.had_studio_override:
                    child_obj.update_studio_values(item)

            child_obj.set_override_state(self._override_state)

        if self._override_state >= OverrideState.PROJECT:
            self._has_project_override = self.had_project_override

        if self._override_state >= OverrideState.STUDIO:
            self._has_studio_override = self.had_studio_override

        self._ignore_child_changes = False

        on_change_trigger.append(self.on_change)

    def add_to_studio_default(self):
        if self._override_state is not OverrideState.STUDIO:
            return
        self._has_studio_override = True
        self.on_change()

    def _remove_from_studio_default(self, on_change_trigger):
        if self._override_state is not OverrideState.STUDIO:
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
            child_obj.set_override_state(self._override_state)

        self._ignore_child_changes = False

        self._has_studio_override = False

        on_change_trigger.append(self.on_change)

    def add_to_project_override(self):
        self._has_project_override = True
        self.on_change()

    def _remove_from_project_override(self, on_change_trigger):
        if self._override_state is not OverrideState.PROJECT:
            return

        if not self.has_project_override:
            return

        if self._has_studio_override:
            value = self._studio_override_value
        elif self.has_default_value:
            value = self._default_value
        else:
            value = self.value_on_not_set

        self._ignore_child_changes = True

        for item in value:
            child_obj = self._add_new_item()
            child_obj.update_default_value(item)
            if self._has_studio_override:
                child_obj.update_studio_values(item)
            child_obj.set_override_state(self._override_state)

        self._ignore_child_changes = False

        self._has_project_override = False

        on_change_trigger.append(self.on_change)

    def reset_callbacks(self):
        super(ListEntity, self).reset_callbacks()
        for child_entity in self.children:
            child_entity.reset_callbacks()
