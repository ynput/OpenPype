import os
import re
import json
import copy

from .exceptions import (
    SchemaTemplateMissingKeys,
    SchemaDuplicatedEnvGroupKeys
)

try:
    STRING_TYPE = basestring
except Exception:
    STRING_TYPE = str

WRAPPER_TYPES = ["form", "collapsible-wrap"]
NOT_SET = type("NOT_SET", (), {"__bool__": lambda obj: False})()
OVERRIDE_VERSION = 1

DEFAULT_VALUES_KEY = "__default_values__"
TEMPLATE_METADATA_KEYS = (
    DEFAULT_VALUES_KEY,
)

template_key_pattern = re.compile(r"(\{.*?[^{0]*\})")




def _fill_inner_schemas(schema_data, schema_collection, schema_templates):
    if schema_data["type"] == "schema":
        raise ValueError("First item in schema data can't be schema.")

    children_key = "children"
    object_type_key = "object_type"
    for item_key in (children_key, object_type_key):
        children = schema_data.get(item_key)
        if not children:
            continue

        if object_type_key == item_key:
            if not isinstance(children, dict):
                continue
            children = [children]

        new_children = []
        for child in children:
            child_type = child["type"]
            if child_type == "schema":
                schema_name = child["name"]
                if schema_name not in schema_collection:
                    if schema_name in schema_templates:
                        raise KeyError((
                            "Schema template \"{}\" is used as `schema`"
                        ).format(schema_name))
                    raise KeyError(
                        "Schema \"{}\" was not found".format(schema_name)
                    )

                filled_child = _fill_inner_schemas(
                    schema_collection[schema_name],
                    schema_collection,
                    schema_templates
                )

            elif child_type in ("template", "schema_template"):
                for filled_child in _fill_schema_template(
                    child, schema_collection, schema_templates
                ):
                    new_children.append(filled_child)
                continue

            else:
                filled_child = _fill_inner_schemas(
                    child, schema_collection, schema_templates
                )

            new_children.append(filled_child)

        if item_key == object_type_key:
            if len(new_children) != 1:
                raise KeyError((
                    "Failed to fill object type with type: {} | name {}"
                ).format(
                    child_type, str(child.get("name"))
                ))
            new_children = new_children[0]

        schema_data[item_key] = new_children
    return schema_data


# TODO reimplement logic inside entities
def validate_environment_groups_uniquenes(
    schema_data, env_groups=None, keys=None
):
    is_first = False
    if env_groups is None:
        is_first = True
        env_groups = {}
        keys = []

    my_keys = copy.deepcopy(keys)
    key = schema_data.get("key")
    if key:
        my_keys.append(key)

    env_group_key = schema_data.get("env_group_key")
    if env_group_key:
        if env_group_key not in env_groups:
            env_groups[env_group_key] = []
        env_groups[env_group_key].append("/".join(my_keys))

    children = schema_data.get("children")
    if not children:
        return

    for child in children:
        validate_environment_groups_uniquenes(
            child, env_groups, copy.deepcopy(my_keys)
        )

    if is_first:
        invalid = {}
        for env_group_key, key_paths in env_groups.items():
            if len(key_paths) > 1:
                invalid[env_group_key] = key_paths

        if invalid:
            raise SchemaDuplicatedEnvGroupKeys(invalid)


def validate_schema(schema_data):
    validate_environment_groups_uniquenes(schema_data)


def get_gui_schema(subfolder, main_schema_name):
    dirpath = os.path.join(
        os.path.dirname(__file__),
        "schemas",
        subfolder
    )
    loaded_schemas = {}
    loaded_schema_templates = {}
    for root, _, filenames in os.walk(dirpath):
        for filename in filenames:
            basename, ext = os.path.splitext(filename)
            if ext != ".json":
                continue

            filepath = os.path.join(root, filename)
            with open(filepath, "r") as json_stream:
                try:
                    schema_data = json.load(json_stream)
                except Exception as exc:
                    raise ValueError((
                        "Unable to parse JSON file {}\n{}"
                    ).format(filepath, str(exc)))
            if isinstance(schema_data, list):
                loaded_schema_templates[basename] = schema_data
            else:
                loaded_schemas[basename] = schema_data

    main_schema = _fill_inner_schemas(
        loaded_schemas[main_schema_name],
        loaded_schemas,
        loaded_schema_templates
    )
    validate_schema(main_schema)
    return main_schema


def get_studio_settings_schema():
    return get_gui_schema("system_schema", "schema_main")


def get_project_settings_schema():
    return get_gui_schema("projects_schema", "schema_main")


class OverrideStateItem:
    """Object used as item for `OverrideState` enum.

    Used object to be able use exact object comparison and value comparisons.
    """
    values = set()

    def __init__(self, value, name):
        self.name = name
        if value in self.__class__.values:
            raise ValueError(
                "Implementation bug: Override State with same value as other."
            )
        self.__class__.values.add(value)
        self.value = value

    def __repr__(self):
        return "<object {}> {} {}".format(
            self.__class__.__name__, self.value, self.name
        )

    def __eq__(self, other):
        """Defines behavior for the equality operator, ==."""
        if isinstance(other, OverrideStateItem):
            return self.value == other.value
        return self.value == other

    def __gt__(self, other):
        """Defines behavior for the greater-than operator, >."""
        if isinstance(other, OverrideStateItem):
            return self.value > other.value
        return self.value > other

    def __lt__(self, other):
        """Defines behavior for the less-than operator, <."""
        if isinstance(other, OverrideStateItem):
            return self.value < other.value
        return self.value < other

    def __le__(self, other):
        """Defines behavior for the less-than-or-equal-to operator, <=."""
        if isinstance(other, OverrideStateItem):
            return self.value == other.value or self.value < other.value
        return self.value == other or self.value < other

    def __ge__(self, other):
        """Defines behavior for the greater-than-or-equal-to operator, >=."""
        if isinstance(other, OverrideStateItem):
            return self.value == other.value or self.value > other.value
        return self.value == other or self.value > other


class OverrideState:
    """Enumeration of override states.

    Each state have unique value.

    Currently has 4 states:
    - NOT_DEFINED - Initial state will raise an error if want to access
        anything in entity.
    - DEFAULTS - Entity cares only about default values. It is not
        possible to set higher state if any entity does not have filled
        default value.
    - STUDIO - First layer of overrides. Hold only studio overriden values
        that are applied on top of defaults.
    - PROJECT - Second layer of overrides. Hold only project overrides that are
        applied on top of defaults and studio overrides.
    """
    NOT_DEFINED = OverrideStateItem(-1, "Not defined")
    DEFAULTS = OverrideStateItem(0, "Defaults")
    STUDIO = OverrideStateItem(1, "Studio overrides")
    PROJECT = OverrideStateItem(2, "Project Overrides")


class SchemasHub:
    def __init__(self, schema_subfolder):
        from openpype.settings import entities

        # Define known abstract classes
        known_abstract_classes = (
            entities.BaseEntity,
            entities.BaseItemEntity,
            entities.ItemEntity,
            entities.EndpointEntity,
            entities.InputEntity,
            entities.BaseEnumEntity
        )

        self._loaded_types = {}
        _gui_types = []
        for attr in dir(entities):
            item = getattr(entities, attr)
            # Filter classes
            if not inspect.isclass(item):
                continue

            # Skip classes that do not inherit from BaseEntity
            if not issubclass(item, entities.BaseEntity):
                continue

            # Skip class that is abstract by design
            if item in known_abstract_classes:
                continue

            if inspect.isabstract(item):
                # Create an object to get crash and get traceback
                item()

            # Backwards compatibility
            # Single entity may have multiple schema types
            for schema_type in item.schema_types:
                self._loaded_types[schema_type] = item

            if item.gui_type:
                _gui_types.append(item)
        self._gui_types = tuple(_gui_types)

        self._schema_subfolder = schema_subfolder
        self._crashed_on_load = {}
        loaded_templates, loaded_schemas = self._load_schemas()

        self._loaded_templates = loaded_templates
        self._loaded_schemas = loaded_schemas

    @property
    def gui_types(self):
        return self._gui_types

    def get_schema(self, schema_name):
        pass

    def get_template(self, template_name):
        pass

    def resolve_schema_data(self, schema_data):
        pass

    def create_schema_object(self, schema_data, *args, **kwargs):
        pass

    def _load_schemas(self):
        dirpath = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "schemas",
            self._schema_subfolder
        )
        loaded_schemas = {}
        loaded_templates = {}
        for root, _, filenames in os.walk(dirpath):
            for filename in filenames:
                basename, ext = os.path.splitext(filename)
                if ext != ".json":
                    continue

                filepath = os.path.join(root, filename)
                with open(filepath, "r") as json_stream:
                    try:
                        schema_data = json.load(json_stream)
                    except Exception as exc:
                        msg = str(exc)
                        print("Unable to parse JSON file {}\n{}".format(
                            filepath, msg
                        ))
                        self._crashed_on_load[basename] = {
                            "filepath": filepath,
                            "message": msg
                        }
                        continue

                if basename in self._crashed_on_load:
                    crashed_item = self._crashed_on_load[basename]
                    raise KeyError((
                        "Duplicated filename \"{}\"."
                        " One of them crashed on load \"{}\" {}"
                    ).format(
                        filename,
                        crashed_item["filpath"],
                        crashed_item["message"]
                    ))

                if isinstance(schema_data, list):
                    if basename in loaded_templates:
                        raise KeyError(
                            "Duplicated template filename \"{}\"".format(
                                filename
                            )
                        )
                    loaded_templates[basename] = schema_data
                else:
                    if basename in loaded_schemas:
                        raise KeyError(
                            "Duplicated schema filename \"{}\"".format(
                                filename
                            )
                        )
                    loaded_schemas[basename] = schema_data

        return loaded_templates, loaded_schemas

    def _fill_schema_template(self, child_data, template_def):
        template_name = child_data["name"]

        # Default value must be dictionary (NOT list)
        # - empty list would not add any item if `template_data` are not filled
        template_data = child_data.get("template_data") or {}
        if isinstance(template_data, dict):
            template_data = [template_data]

        skip_paths = child_data.get("skip_paths") or []
        if isinstance(skip_paths, STRING_TYPE):
            skip_paths = [skip_paths]

        output = []
        for single_template_data in template_data:
            try:
                output.extend(self._fill_schema_template_data(
                    template_def, single_template_data, skip_paths
                ))

            except SchemaTemplateMissingKeys as exc:
                raise SchemaTemplateMissingKeys(
                    exc.missing_keys, exc.required_keys, template_name
                )
        return output

    def _fill_schema_template_data(
        self,
        template,
        template_data,
        skip_paths,
        required_keys=None,
        missing_keys=None
    ):
        first = False
        if required_keys is None:
            first = True

            if "skip_paths" in template_data:
                skip_paths = template_data["skip_paths"]
                if not isinstance(skip_paths, list):
                    skip_paths = [skip_paths]

            # Cleanup skip paths (skip empty values)
            skip_paths = [path for path in skip_paths if path]

            required_keys = set()
            missing_keys = set()

            # Copy template data as content may change
            template = copy.deepcopy(template)

            # Get metadata item from template
            metadata_item = self._pop_metadata_item(template)

            # Check for default values for template data
            default_values = metadata_item.get(DEFAULT_VALUES_KEY) or {}

            for key, value in default_values.items():
                if key not in template_data:
                    template_data[key] = value

        if not template:
            output = template

        elif isinstance(template, list):
            # Store paths by first part if path
            # - None value says that whole key should be skipped
            skip_paths_by_first_key = {}
            for path in skip_paths:
                parts = path.split("/")
                key = parts.pop(0)
                if key not in skip_paths_by_first_key:
                    skip_paths_by_first_key[key] = []

                value = "/".join(parts)
                skip_paths_by_first_key[key].append(value or None)

            output = []
            for item in template:
                # Get skip paths for children item
                _skip_paths = []
                if not isinstance(item, dict):
                    pass

                elif item.get("type") in WRAPPER_TYPES:
                    _skip_paths = copy.deepcopy(skip_paths)

                elif skip_paths_by_first_key:
                    # Check if this item should be skipped
                    key = item.get("key")
                    if key and key in skip_paths_by_first_key:
                        _skip_paths = skip_paths_by_first_key[key]
                        # Skip whole item if None is in skip paths value
                        if None in _skip_paths:
                            continue

                output_item = self._fill_schema_template_data(
                    item,
                    template_data,
                    _skip_paths,
                    required_keys,
                    missing_keys
                )
                if output_item:
                    output.append(output_item)

        elif isinstance(template, dict):
            output = {}
            for key, value in template.items():
                output[key] = self._fill_schema_template_data(
                    value,
                    template_data,
                    skip_paths,
                    required_keys,
                    missing_keys
                )
            if (
                output.get("type") in WRAPPER_TYPES
                and not output.get("children")
            ):
                return {}

        elif isinstance(template, STRING_TYPE):
            # TODO find much better way how to handle filling template data
            template = (
                template
                .replace("{{", "__dbcb__")
                .replace("}}", "__decb__")
            )
            for replacement_string in template_key_pattern.findall(template):
                key = str(replacement_string[1:-1])
                required_keys.add(key)
                if key not in template_data:
                    missing_keys.add(key)
                    continue

                value = template_data[key]
                if replacement_string == template:
                    # Replace the value with value from templates data
                    # - with this is possible to set value with different type
                    template = value
                else:
                    # Only replace the key in string
                    template = template.replace(replacement_string, value)

            output = template.replace("__dbcb__", "{").replace("__decb__", "}")

        else:
            output = template

        if first and missing_keys:
            raise SchemaTemplateMissingKeys(missing_keys, required_keys)

        return output

    def _pop_metadata_item(self, template_def):
        found_idx = None
        for idx, item in enumerate(template_def):
            if not isinstance(item, dict):
                continue

            for key in TEMPLATE_METADATA_KEYS:
                if key in item:
                    found_idx = idx
                    break

            if found_idx is not None:
                break

        metadata_item = {}
        if found_idx is not None:
            metadata_item = template_def.pop(found_idx)
        return metadata_item
