import os
import json
import copy
import inspect

from abc import abstractmethod

from .base_entity import BaseItemEntity
from .lib import (
    NOT_SET,
    WRAPPER_TYPES,
    OverrideState,
    gui_schema
)
from pype.settings.constants import SYSTEM_SETTINGS_KEY

from pype.settings.lib import (
    DEFAULTS_DIR,

    get_default_settings,

    get_studio_system_settings_overrides,

    save_studio_settings,

    find_environments,
    apply_overrides
)
# TODO implement
# ProjectSettings
# AnatomySettings


class RootEntity(BaseItemEntity):
    schema_types = ["root"]

    def __init__(self, schema_data, reset):
        super(RootEntity, self).__init__(schema_data)
        self.root_item = self
        self.item_initalization()
        if reset:
            self.reset()

    @abstractmethod
    def reset(self):
        pass

    def __getitem__(self, key):
        return self.non_gui_children[key]

    def __setitem__(self, key, value):
        self.non_gui_children[key].set(value)

    def __iter__(self):
        for key in self.keys():
            yield key

    def get(self, key, default=None):
        return self.non_gui_children.get(key, default)

    def keys(self):
        return self.non_gui_children.keys()

    def values(self):
        return self.non_gui_children.values()

    def items(self):
        return self.non_gui_children.items()

    def _add_children(self, schema_data, first=True):
        added_children = []
        for children_schema in schema_data["children"]:
            if children_schema["type"] in WRAPPER_TYPES:
                _children_schema = copy.deepcopy(children_schema)
                wrapper_children = self._add_children(
                    children_schema["children"], False
                )
                _children_schema["children"] = wrapper_children
                added_children.append(_children_schema)
                continue

            child_obj = self.create_schema_object(children_schema, self)
            self.children.append(child_obj)
            added_children.append(child_obj)
            if type(child_obj) in self._gui_types:
                continue

            if child_obj.key in self.non_gui_children:
                raise KeyError("Duplicated key \"{}\"".format(child_obj.key))
            self.non_gui_children[child_obj.key] = child_obj

        if not first:
            return added_children

        for child_obj in added_children:
            self.gui_layout.append(child_obj)

    def item_initalization(self):
        self._loaded_types = None
        self._gui_types = None
        # Children are stored by key as keys are immutable and are defined by
        # schema
        self.valid_value_types = (dict, )
        self.children = []
        self.non_gui_children = {}
        self.gui_layout = []
        self._add_children(self.schema_data)
        for children in self.children:
            children.schema_validations()

    def create_schema_object(self, schema_data, *args, **kwargs):
        if self._loaded_types is None:
            from pype.settings import entities

            known_abstract_classes = (
                entities.BaseEntity,
                entities.BaseItemEntity,
                entities.ItemEntity,
                entities.InputEntity
            )

            self._loaded_types = {}
            self._gui_types = []
            for attr in dir(entities):
                item = getattr(entities, attr)
                if not inspect.isclass(item):
                    continue

                if not issubclass(item, entities.BaseEntity):
                    continue

                if inspect.isabstract(item):
                    if item in known_abstract_classes:
                        continue
                    item()

                for schema_type in item.schema_types:
                    self._loaded_types[schema_type] = item

                gui_type = getattr(item, "gui_type", False)
                if gui_type:
                    self._gui_types.append(item)

        klass = self._loaded_types.get(schema_data["type"])
        if not klass:
            raise KeyError("Unknown type \"{}\"".format(schema_data["type"]))

        return klass(schema_data, *args, **kwargs)

    def set_override_state(self, state):
        self.override_state = state
        for child_obj in self.non_gui_children.values():
            child_obj.set_override_state(state)

    def set(self, value):
        for _key, _value in value.items():
            self.non_gui_children[_key].set(_value)

    def on_change(self):
        for callback in self.on_change_callbacks:
            callback()

    def on_child_change(self, child_obj):
        self.on_change()

    def get_child_path(self, child_obj):
        for key, _child_obj in self.non_gui_children.items():
            if _child_obj is child_obj:
                return key
        raise ValueError("Didn't found child {}".format(child_obj))

    @property
    def value(self):
        output = {}
        for key, child_obj in self.non_gui_children.items():
            output[key] = child_obj.value
        return output

    def settings_value(self):
        if self.override_state is OverrideState.NOT_DEFINED:
            return NOT_SET

        if self.override_state is not OverrideState.DEFAULTS:
            output = {}
            for key, child_obj in self.non_gui_children.items():
                value = child_obj.settings_value()
                if value is not NOT_SET:
                    output[key] = value
            return output

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

    @property
    def child_has_studio_override(self):
        if self.override_state >= OverrideState.STUDIO:
            for child_obj in self.non_gui_children.values():
                if child_obj.child_has_studio_override:
                    return True
        return False

    @property
    def child_has_project_override(self):
        if self.override_state >= OverrideState.PROJECT:
            for child_obj in self.non_gui_children.values():
                if child_obj.child_has_project_override:
                    return True
        return False

    @property
    def has_unsaved_changes(self):
        return self.child_is_modified

    @property
    def child_is_modified(self):
        for child_obj in self.non_gui_children.values():
            if child_obj.has_unsaved_changes:
                return True
        return False

    def _discard_changes(self, on_change_trigger):
        for child_obj in self.non_gui_children.values():
            child_obj.discard_changes(on_change_trigger)

    def add_to_studio_default(self):
        for child_obj in self.non_gui_children.values():
            child_obj.add_to_studio_default()

    def _remove_from_studio_default(self, on_change_trigger):
        for child_obj in self.non_gui_children.values():
            child_obj.remove_from_studio_default(on_change_trigger)

    def add_to_project_override(self):
        for child_obj in self.non_gui_children.values():
            child_obj.add_to_project_override()

    def _remove_from_project_override(self):
        for child_obj in self.non_gui_children.values():
            child_obj.remove_from_project_override()

    def save(self):
        if self.override_state is OverrideState.NOT_DEFINED:
            raise ValueError(
                "Can't save if override state is set to NOT_DEFINED"
            )

        if self.override_state is OverrideState.DEFAULTS:
            self.save_default_values()

        elif self.override_state is OverrideState.STUDIO:
            self.save_studio_values()

        elif self.override_state is OverrideState.PROJECT:
            self.save_project_values()

        self.reset()

    @abstractmethod
    def defaults_dir(self):
        pass

    @abstractmethod
    def validate_defaults_to_save(self, value):
        pass

    def save_default_values(self):
        settings_value = self.settings_value()
        self.validate_defaults_to_save(settings_value)

        defaults_dir = self.defaults_dir()
        for file_path, value in settings_value.items():
            subpath = file_path + ".json"

            output_path = os.path.join(defaults_dir, subpath)
            dirpath = os.path.dirname(output_path)
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)

            print("Saving data to: ", subpath)
            with open(output_path, "w") as file_stream:
                json.dump(value, file_stream, indent=4)

    @abstractmethod
    def save_studio_values(self):
        pass

    @abstractmethod
    def save_project_values(self):
        pass

    def is_in_defaults_state(self):
        return self.override_state is OverrideState.DEFAULTS

    def is_in_studio_state(self):
        return self.override_state is OverrideState.STUDIO

    def is_in_project_state(self):
        return self.override_state is OverrideState.PROJECT

    def set_defaults_state(self):
        self.set_override_state(OverrideState.DEFAULTS)

    def set_studio_state(self):
        self.set_override_state(OverrideState.STUDIO)

    def set_project_state(self):
        self.set_override_state(OverrideState.PROJECT)


class SystemSettings(RootEntity):
    def __init__(
        self, set_studio_state=True, reset=True, schema_data=None
    ):
        if schema_data is None:
            schema_data = gui_schema("system_schema", "schema_main")

        super(SystemSettings, self).__init__(schema_data, reset)

        if set_studio_state:
            self.set_studio_state()

    def _reset_values(self):
        default_value = get_default_settings()[SYSTEM_SETTINGS_KEY]
        for key, child_obj in self.non_gui_children.items():
            value = default_value.get(key, NOT_SET)
            child_obj.update_default_value(value)

        studio_overrides = get_studio_system_settings_overrides()
        for key, child_obj in self.non_gui_children.items():
            value = studio_overrides.get(key, NOT_SET)
            child_obj.update_studio_values(value)

    def reset(self, new_state=None):
        if new_state is None:
            new_state = self.override_state

        if new_state is OverrideState.NOT_DEFINED:
            new_state = OverrideState.DEFAULTS

        if new_state is OverrideState.PROJECT:
            raise ValueError("System settings can't store poject overrides.")

        self._reset_values()
        self.set_override_state(new_state)

    def defaults_dir(self):
        return os.path.join(DEFAULTS_DIR, SYSTEM_SETTINGS_KEY)

    def save_studio_values(self):
        settings_value = self.settings_value()
        self.validate_duplicated_env_group(settings_value)
        print("Saving system settings: ", json.dumps(settings_value, indent=4))
        save_studio_settings(settings_value)

    def validate_defaults_to_save(self, value):
        self.validate_duplicated_env_group(value)

    def validate_duplicated_env_group(self, value, override_state=None):
        """
        Raises:
            DuplicatedEnvGroups: When value contain duplicated env groups.
        """
        value = copy.deepcopy(value)
        if override_state is None:
            override_state = self.override_state

        if override_state is OverrideState.STUDIO:
            default_values = get_default_settings()[SYSTEM_SETTINGS_KEY]
            final_value = apply_overrides(default_values, value)
        else:
            final_value = value

        # Check if final_value contain duplicated environment groups
        find_environments(final_value)

    def save_project_values(self):
        raise ValueError("System settings can't save project overrides.")
