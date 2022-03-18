import copy
from .input_entities import InputEntity
from .exceptions import EntitySchemaError
from .lib import NOT_SET, STRING_TYPE


class BaseEnumEntity(InputEntity):
    def _item_initialization(self):
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
                reason = 'Key "{}" is more than once in enum items.'.format(
                    key
                )
                raise EntitySchemaError(self, reason)

            enum_keys.add(key)

            if not isinstance(key, STRING_TYPE):
                reason = 'Key "{}" has invalid type {}, expected {}.'.format(
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
                    '{} Invalid value "{}". Expected one of: {}'.format(
                        self.path, item, self.valid_keys
                    )
                )
        self._current_value = new_value
        self._on_value_change()


class EnumEntity(BaseEnumEntity):
    schema_types = ["enum"]

    def _item_initialization(self):
        self.multiselection = self.schema_data.get("multiselection", False)
        self.enum_items = self.schema_data.get("enum_items")
        # Default is optional and non breaking attribute
        enum_default = self.schema_data.get("default")

        all_keys = []
        for item in self.enum_items or []:
            key = tuple(item.keys())[0]
            all_keys.append(key)

        self.valid_keys = set(all_keys)

        if self.multiselection:
            self.valid_value_types = (list,)
            value_on_not_set = []
            if enum_default:
                if not isinstance(enum_default, list):
                    enum_default = [enum_default]

                for item in enum_default:
                    if item in all_keys:
                        value_on_not_set.append(item)

            self.value_on_not_set = value_on_not_set

        else:
            if isinstance(enum_default, list) and enum_default:
                enum_default = enum_default[0]

            if enum_default in self.valid_keys:
                self.value_on_not_set = enum_default

            else:
                for key in all_keys:
                    if self.value_on_not_set is NOT_SET:
                        self.value_on_not_set = key
                        break

            self.valid_value_types = (STRING_TYPE,)

        # GUI attribute
        self.placeholder = self.schema_data.get("placeholder")

    def schema_validations(self):
        if not self.enum_items and "enum_items" not in self.schema_data:
            raise EntitySchemaError(
                self, "Enum item must have defined `enum_items`"
            )
        super(EnumEntity, self).schema_validations()

    def set_override_state(self, *args, **kwargs):
        super(EnumEntity, self).set_override_state(*args, **kwargs)

        # Make sure current value is valid
        if self.multiselection:
            new_value = []
            for key in self._current_value:
                if key in self.valid_keys:
                    new_value.append(key)
            self._current_value = new_value

        elif self._current_value not in self.valid_keys:
            self._current_value = self.value_on_not_set


class HostsEnumEntity(BaseEnumEntity):
    """Enumeration of host names.

    Enum items are hardcoded in definition of the entity.

    Hosts enum can have defined empty value as valid option which is
    represented by empty string. Schema key to set this option is
    `use_empty_value` (true/false). And to set label of empty value set
    `empty_label` (string).

    Enum can have single and multiselection.

    NOTE:
    Host name is not the same as application name. Host name defines
    implementation instead of application name.
    """

    schema_types = ["hosts-enum"]
    all_host_names = [
        "aftereffects",
        "blender",
        "celaction",
        "flame",
        "fusion",
        "harmony",
        "hiero",
        "houdini",
        "maya",
        "nuke",
        "photoshop",
        "resolve",
        "tvpaint",
        "unreal",
        "standalonepublisher",
        "webpublisher",
    ]

    def _item_initialization(self):
        self.multiselection = self.schema_data.get("multiselection", True)
        use_empty_value = False
        if not self.multiselection:
            use_empty_value = self.schema_data.get(
                "use_empty_value", use_empty_value
            )
        self.use_empty_value = use_empty_value

        hosts_filter = self.schema_data.get("hosts_filter") or []
        self.hosts_filter = hosts_filter

        custom_labels = self.schema_data.get("custom_labels") or {}

        host_names = copy.deepcopy(self.all_host_names)
        if hosts_filter:
            for host_name in tuple(host_names):
                if host_name not in hosts_filter:
                    host_names.remove(host_name)

        if self.use_empty_value:
            host_names.insert(0, "")
            # Add default label for empty value if not available
            if "" not in custom_labels:
                custom_labels[""] = "< without host >"

        # These are hardcoded there is not list of available host in OpenPype
        enum_items = []
        valid_keys = set()
        for key in host_names:
            label = custom_labels.get(key, key)
            valid_keys.add(key)
            enum_items.append({key: label})

        self.enum_items = enum_items
        self.valid_keys = valid_keys

        if self.multiselection:
            self.valid_value_types = (list,)
            self.value_on_not_set = []
        else:
            for key in valid_keys:
                if self.value_on_not_set is NOT_SET:
                    self.value_on_not_set = key
                    break

            self.valid_value_types = (STRING_TYPE,)

        # GUI attribute
        self.placeholder = self.schema_data.get("placeholder")

    def schema_validations(self):
        if self.hosts_filter:
            enum_len = len(self.enum_items)
            if enum_len == 0 or (enum_len == 1 and self.use_empty_value):
                joined_filters = ", ".join(
                    ['"{}"'.format(item) for item in self.hosts_filter]
                )
                reason = (
                    "All host names were removed after applying"
                    " host filters. {}"
                ).format(joined_filters)
                raise EntitySchemaError(self, reason)

            invalid_filters = set()
            for item in self.hosts_filter:
                if item not in self.all_host_names:
                    invalid_filters.add(item)

            if invalid_filters:
                joined_filters = ", ".join(
                    ['"{}"'.format(item) for item in self.hosts_filter]
                )
                expected_hosts = ", ".join(
                    ['"{}"'.format(item) for item in self.all_host_names]
                )
                self.log.warning(
                    (
                        "Host filters containt invalid host names:"
                        ' "{}" Expected values are {}'
                    ).format(joined_filters, expected_hosts)
                )

        super(HostsEnumEntity, self).schema_validations()


class AppsEnumEntity(BaseEnumEntity):
    """Enum of applications for project anatomy attributes."""

    schema_types = ["apps-enum"]

    def _item_initialization(self):
        self.multiselection = True
        self.value_on_not_set = []
        self.enum_items = []
        self.valid_keys = set()
        self.valid_value_types = (list,)
        self.placeholder = None

    def _get_enum_values(self):
        system_settings_entity = self.get_entity_from_path("system_settings")

        valid_keys = set()
        enum_items_list = []
        applications_entity = system_settings_entity["applications"]
        app_entities = {}
        additional_app_names = set()
        additional_apps_entity = None
        for group_name, app_group in applications_entity.items():
            if group_name != "additional_apps":
                app_entities[group_name] = app_group
                continue

            additional_apps_entity = app_group
            for _group_name, _group in app_group.items():
                additional_app_names.add(_group_name)
                app_entities[_group_name] = _group

        for group_name, app_group in app_entities.items():
            enabled_entity = app_group.get("enabled")
            if enabled_entity and not enabled_entity.value:
                continue

            if group_name in additional_app_names:
                group_label = additional_apps_entity.get_key_label(group_name)
                if not group_label:
                    group_label = group_name
            else:
                group_label = app_group["label"].value
            variants_entity = app_group["variants"]
            for variant_name, variant_entity in variants_entity.items():
                enabled_entity = variant_entity.get("enabled")
                if enabled_entity and not enabled_entity.value:
                    continue

                variant_label = None
                if "variant_label" in variant_entity:
                    variant_label = variant_entity["variant_label"].value
                elif hasattr(variants_entity, "get_key_label"):
                    variant_label = variants_entity.get_key_label(variant_name)

                if not variant_label:
                    variant_label = variant_name

                if group_label:
                    full_label = "{} {}".format(group_label, variant_label)
                else:
                    full_label = variant_label

                full_name = "/".join((group_name, variant_name))
                enum_items_list.append((full_name, full_label))
                valid_keys.add(full_name)

        enum_items = []
        for key, value in sorted(enum_items_list, key=lambda item: item[1]):
            enum_items.append({key: value})
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

    def _item_initialization(self):
        self.multiselection = True
        self.value_on_not_set = []
        self.enum_items = []
        self.valid_keys = set()
        self.valid_value_types = (list,)
        self.placeholder = None

    def _get_enum_values(self):
        system_settings_entity = self.get_entity_from_path("system_settings")

        valid_keys = set()
        enum_items_list = []
        tool_groups_entity = system_settings_entity["tools"]["tool_groups"]
        for group_name, tool_group in tool_groups_entity.items():
            # Try to get group label from entity
            group_label = None
            if hasattr(tool_groups_entity, "get_key_label"):
                group_label = tool_groups_entity.get_key_label(group_name)

            variants_entity = tool_group["variants"]
            for variant_name in variants_entity.keys():
                # Prepare tool name (used as value)
                tool_name = "/".join((group_name, variant_name))

                # Try to get variant label from entity
                variant_label = None
                if hasattr(variants_entity, "get_key_label"):
                    variant_label = variants_entity.get_key_label(variant_name)

                # Tool label that will be shown
                # - use tool name itself if labels are not filled
                if group_label and variant_label:
                    tool_label = " ".join((group_label, variant_label))
                else:
                    tool_label = tool_name

                enum_items_list.append((tool_name, tool_label))
                valid_keys.add(tool_name)

        enum_items = []
        for key, value in sorted(enum_items_list, key=lambda item: item[1]):
            enum_items.append({key: value})
        return enum_items, valid_keys

    def set_override_state(self, *args, **kwargs):
        super(ToolsEnumEntity, self).set_override_state(*args, **kwargs)

        self.enum_items, self.valid_keys = self._get_enum_values()
        new_value = []
        for key in self._current_value:
            if key in self.valid_keys:
                new_value.append(key)
        self._current_value = new_value


class TaskTypeEnumEntity(BaseEnumEntity):
    schema_types = ["task-types-enum"]

    def _item_initialization(self):
        self.multiselection = self.schema_data.get("multiselection", True)
        if self.multiselection:
            self.valid_value_types = (list,)
            self.value_on_not_set = []
        else:
            self.valid_value_types = (STRING_TYPE,)
            self.value_on_not_set = ""

        self.enum_items = []
        self.valid_keys = set()
        self.placeholder = None

    def _get_enum_values(self):
        anatomy_entity = self.get_entity_from_path(
            "project_settings/project_anatomy"
        )

        valid_keys = set()
        enum_items = []
        for task_type in anatomy_entity["tasks"].keys():
            enum_items.append({task_type: task_type})
            valid_keys.add(task_type)

        return enum_items, valid_keys

    def _convert_value_for_current_state(self, source_value):
        if self.multiselection:
            output = []
            for key in source_value:
                if key in self.valid_keys:
                    output.append(key)
            return output

        if source_value not in self.valid_keys:
            # Take first item from enum items
            for item in self.enum_items:
                for key in item.keys():
                    source_value = key
                break
        return source_value

    def set_override_state(self, *args, **kwargs):
        super(TaskTypeEnumEntity, self).set_override_state(*args, **kwargs)

        self.enum_items, self.valid_keys = self._get_enum_values()

        if self.multiselection:
            new_value = []
            for key in self._current_value:
                if key in self.valid_keys:
                    new_value.append(key)

            if self._current_value != new_value:
                self.set(new_value)
        else:
            if not self.enum_items:
                self.valid_keys.add("")
                self.enum_items.append({"": "< Empty >"})

            for item in self.enum_items:
                for key in item.keys():
                    value_on_not_set = key
                break

            self.value_on_not_set = value_on_not_set
            if (
                self._current_value is NOT_SET
                or self._current_value not in self.valid_keys
            ):
                self.set(value_on_not_set)


class DeadlineUrlEnumEntity(BaseEnumEntity):
    schema_types = ["deadline_url-enum"]

    def _item_initialization(self):
        self.multiselection = self.schema_data.get("multiselection", True)

        self.enum_items = []
        self.valid_keys = set()

        if self.multiselection:
            self.valid_value_types = (list,)
            self.value_on_not_set = []
        else:
            self.valid_value_types = (STRING_TYPE,)
            self.value_on_not_set = ""

        # GUI attribute
        self.placeholder = self.schema_data.get("placeholder")

    def _get_enum_values(self):
        deadline_urls_entity = self.get_entity_from_path(
            "system_settings/modules/deadline/deadline_urls"
        )

        valid_keys = set()
        enum_items_list = []
        for server_name, url_entity in deadline_urls_entity.items():
            enum_items_list.append(
                {server_name: "{}: {}".format(server_name, url_entity.value)}
            )
            valid_keys.add(server_name)
        return enum_items_list, valid_keys

    def set_override_state(self, *args, **kwargs):
        super(DeadlineUrlEnumEntity, self).set_override_state(*args, **kwargs)

        self.enum_items, self.valid_keys = self._get_enum_values()
        if self.multiselection:
            new_value = []
            for key in self._current_value:
                if key in self.valid_keys:
                    new_value.append(key)
            self._current_value = new_value

        else:
            if not self.valid_keys:
                self._current_value = ""

            elif self._current_value not in self.valid_keys:
                self._current_value = tuple(self.valid_keys)[0]


class ShotgridUrlEnumEntity(BaseEnumEntity):
    schema_types = ["shotgrid_url-enum"]

    def _item_initialization(self):
        self.multiselection = False

        self.enum_items = []
        self.valid_keys = set()

        self.valid_value_types = (STRING_TYPE,)
        self.value_on_not_set = ""

        # GUI attribute
        self.placeholder = self.schema_data.get("placeholder")

    def _get_enum_values(self):
        shotgrid_settings = self.get_entity_from_path(
            "system_settings/modules/shotgrid/shotgrid_settings"
        )

        valid_keys = set()
        enum_items_list = []
        for server_name, settings in shotgrid_settings.items():
            enum_items_list.append(
                {
                    server_name: "{}: {}".format(
                        server_name, settings["shotgrid_url"].value
                    )
                }
            )
            valid_keys.add(server_name)
        return enum_items_list, valid_keys

    def set_override_state(self, *args, **kwargs):
        super(ShotgridUrlEnumEntity, self).set_override_state(*args, **kwargs)

        self.enum_items, self.valid_keys = self._get_enum_values()
        if not self.valid_keys:
            self._current_value = ""

        elif self._current_value not in self.valid_keys:
            self._current_value = tuple(self.valid_keys)[0]


class AnatomyTemplatesEnumEntity(BaseEnumEntity):
    schema_types = ["anatomy-templates-enum"]

    def _item_initialization(self):
        self.multiselection = False

        self.enum_items = []
        self.valid_keys = set()

        enum_default = self.schema_data.get("default") or "work"

        self.value_on_not_set = enum_default
        self.valid_value_types = (STRING_TYPE,)

        # GUI attribute
        self.placeholder = self.schema_data.get("placeholder")

    def _get_enum_values(self):
        templates_entity = self.get_entity_from_path(
            "project_anatomy/templates"
        )

        valid_keys = set()
        enum_items_list = []

        others_entity = None
        for key, entity in templates_entity.items():
            # Skip defaults key
            if key == "defaults":
                continue

            if key == "others":
                others_entity = entity
                continue

            label = key
            if hasattr(entity, "label"):
                label = entity.label or label

            enum_items_list.append({key: label})
            valid_keys.add(key)

        if others_entity is not None:
            get_child_label_func = getattr(
                others_entity, "get_child_label", None
            )
            for key, child_entity in others_entity.items():
                label = key
                if callable(get_child_label_func):
                    label = get_child_label_func(child_entity) or label

                enum_items_list.append({key: label})
                valid_keys.add(key)

        return enum_items_list, valid_keys

    def set_override_state(self, *args, **kwargs):
        super(AnatomyTemplatesEnumEntity, self).set_override_state(
            *args, **kwargs
        )

        self.enum_items, self.valid_keys = self._get_enum_values()
        if self._current_value not in self.valid_keys:
            self._current_value = self.value_on_not_set
