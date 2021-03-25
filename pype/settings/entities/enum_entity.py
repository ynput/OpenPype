from .input_entities import InputEntity
from .exceptions import EntitySchemaError
from .lib import (
    NOT_SET,
    STRING_TYPE
)


class BaseEnumEntity(InputEntity):
    def _item_initalization(self):
        self.multiselection = True
        self.value_on_not_set = None
        self.enum_items = None
        self.valid_keys = None
        self.valid_value_types = None
        self.placeholder = None

    def schema_validations(self):
        if not isinstance(self.enum_items, list):
            raise EntitySchemaError(
                self, "Enum item must have defined `enum_items` as list."
            )

        enum_keys = set()
        for item in self.enum_items:
            key = tuple(item.keys())[0]
            if key in enum_keys:
                reason = "Key \"{}\" is more than once in enum items.".format(
                    key
                )
                raise EntitySchemaError(self, reason)

            enum_keys.add(key)

            if not isinstance(key, STRING_TYPE):
                reason = "Key \"{}\" has invalid type {}, expected {}.".format(
                    key, type(key), STRING_TYPE
                )
                raise EntitySchemaError(self, reason)

        super(BaseEnumEntity, self).schema_validations()

    def _convert_to_valid_type(self, value):
        if self.multiselection:
            if isinstance(value, (set, tuple)):
                return list(value)
        elif isinstance(value, (int, float)):
            return str(value)
        return NOT_SET

    def set(self, value):
        new_value = self.convert_to_valid_type(value)
        if self.multiselection:
            check_values = new_value
        else:
            check_values = [new_value]

        for item in check_values:
            if item not in self.valid_keys:
                raise ValueError(
                    "{} Invalid value \"{}\". Expected one of: {}".format(
                        self.path, item, self.valid_keys
                    )
                )
        self._current_value = new_value
        self._on_value_change()


class EnumEntity(BaseEnumEntity):
    schema_types = ["enum"]

    def _item_initalization(self):
        self.multiselection = self.schema_data.get("multiselection", False)
        self.enum_items = self.schema_data.get("enum_items")

        valid_keys = set()
        for item in self.enum_items or []:
            valid_keys.add(tuple(item.keys())[0])

        self.valid_keys = valid_keys

        if self.multiselection:
            self.valid_value_types = (list, )
            self.value_on_not_set = []
        else:
            for key in valid_keys:
                if self.value_on_not_set is NOT_SET:
                    self.value_on_not_set = key
                    break

            self.valid_value_types = (STRING_TYPE, )

        # GUI attribute
        self.placeholder = self.schema_data.get("placeholder")

    def schema_validations(self):
        if not self.enum_items and "enum_items" not in self.schema_data:
            raise EntitySchemaError(
                self, "Enum item must have defined `enum_items`"
            )
        super(EnumEntity, self).schema_validations()


class AppsEnumEntity(BaseEnumEntity):
    schema_types = ["apps-enum"]

    def _item_initalization(self):
        self.multiselection = True
        self.value_on_not_set = []
        self.enum_items = []
        self.valid_keys = set()
        self.valid_value_types = (list, )
        self.placeholder = None

    def _get_enum_values(self):
        system_settings_entity = self.get_entity_from_path("system_settings")

        valid_keys = set()
        enum_items = []
        for app_group in system_settings_entity["applications"].values():
            enabled_entity = app_group.get("enabled")
            if enabled_entity and not enabled_entity.value:
                continue

            host_name_entity = app_group.get("host_name")
            if not host_name_entity or not host_name_entity.value:
                continue

            group_label = app_group["label"].value

            for variant_name, variant_entity in app_group["variants"].items():
                enabled_entity = variant_entity.get("enabled")
                if enabled_entity and not enabled_entity.value:
                    continue

                _group_label = variant_entity["label"].value
                if not _group_label:
                    _group_label = group_label
                variant_label = variant_entity["variant_label"].value

                full_label = "{} {}".format(_group_label, variant_label)
                enum_items.append({variant_name: full_label})
                valid_keys.add(variant_name)
        return enum_items, valid_keys

    def set_override_state(self, *args, **kwargs):
        super(AppsEnumEntity, self).set_override_state(*args, **kwargs)

        self.enum_items, self.valid_keys = self._get_enum_values()
        new_value = []
        for key in self._current_value:
            if key in self.valid_keys:
                new_value.append(key)
        self._current_value = new_value


class ToolsEnumEntity(BaseEnumEntity):
    schema_types = ["tools-enum"]

    def _item_initalization(self):
        self.multiselection = True
        self.value_on_not_set = []
        self.enum_items = []
        self.valid_keys = set()
        self.valid_value_types = (list, )
        self.placeholder = None

    def _get_enum_values(self):
        system_settings_entity = self.get_entity_from_path("system_settings")

        valid_keys = set()
        enum_items = []
        tools_entity = system_settings_entity["tools"]
        for group_name, tool_group in tools_entity["tool_groups"].items():
            for variant_name in tool_group["variants"].keys():
                tool_name = "/".join((group_name, variant_name))
                enum_items.append({tool_name: tool_name})
                valid_keys.add(tool_name)
        return enum_items, valid_keys

    def set_override_state(self, *args, **kwargs):
        super(ToolsEnumEntity, self).set_override_state(*args, **kwargs)

        self.enum_items, self.valid_keys = self._get_enum_values()
        new_value = []
        for key in self._current_value:
            if key in self.valid_keys:
                new_value.append(key)
        self._current_value = new_value
