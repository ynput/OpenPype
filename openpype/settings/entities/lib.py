import os
import re
import json
import copy
import inspect
import collections
import contextlib

from .exceptions import (
    SchemaTemplateMissingKeys,
    SchemaDuplicatedEnvGroupKeys
)

from openpype.settings.constants import (
    SYSTEM_SETTINGS_KEY,
    PROJECT_SETTINGS_KEY,
    SCHEMA_KEY_SYSTEM_SETTINGS,
    SCHEMA_KEY_PROJECT_SETTINGS
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

SCHEMA_EXTEND_TYPES = (
    "schema", "template", "schema_template", "dynamic_schema"
)

template_key_pattern = re.compile(r"(\{.*?[^{0]*\})")


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
    - STUDIO - First layer of overrides. Hold only studio overridden values
        that are applied on top of defaults.
    - PROJECT - Second layer of overrides. Hold only project overrides that are
        applied on top of defaults and studio overrides.
    """
    NOT_DEFINED = OverrideStateItem(-1, "Not defined")
    DEFAULTS = OverrideStateItem(0, "Defaults")
    STUDIO = OverrideStateItem(1, "Studio overrides")
    PROJECT = OverrideStateItem(2, "Project Overrides")


class SchemasHub:
    def __init__(self, schema_type, reset=True):
        self._schema_type = schema_type

        self._loaded_types = {}
        self._gui_types = tuple()

        self._crashed_on_load = {}
        self._loaded_templates = {}
        self._loaded_schemas = {}

        # Attributes for modules settings
        self._dynamic_schemas_defs_by_id = {}
        self._dynamic_schemas_by_id = {}

        # Store validating and validated dynamic template or schemas
        self._validating_dynamic = set()
        self._validated_dynamic = set()

        # Trigger reset
        if reset:
            self.reset()

    @property
    def schema_type(self):
        return self._schema_type

    def reset(self):
        self._load_modules_settings_defs()
        self._load_types()
        self._load_schemas()

    def _load_modules_settings_defs(self):
        from openpype.modules import get_module_settings_defs

        module_settings_defs = get_module_settings_defs()
        for module_settings_def_cls in module_settings_defs:
            module_settings_def = module_settings_def_cls()
            def_id = module_settings_def.id
            self._dynamic_schemas_defs_by_id[def_id] = module_settings_def

    @property
    def gui_types(self):
        return self._gui_types

    def resolve_dynamic_schema(self, dynamic_key):
        output = []
        for def_id, def_keys in self._dynamic_schemas_by_id.items():
            if dynamic_key in def_keys:
                def_schema = def_keys[dynamic_key]
                if not def_schema:
                    continue

                if isinstance(def_schema, dict):
                    def_schema = [def_schema]

                all_def_schema = []
                for item in def_schema:
                    items = self.resolve_schema_data(item)
                    for _item in items:
                        _item["_dynamic_schema_id"] = def_id
                    all_def_schema.extend(items)
                output.extend(all_def_schema)
        return output

    def get_template_name(self, item_def, default=None):
        """Get template name from passed item definition.

        Args:
            item_def(dict): Definition of item with "type".
            default(object): Default return value.
        """
        output = default
        if not item_def or not isinstance(item_def, dict):
            return output

        item_type = item_def.get("type")
        if item_type in ("template", "schema_template"):
            output = item_def["name"]
        return output

    def is_dynamic_template_validating(self, template_name):
        """Is template validating using different entity.

        Returns:
            bool: Is template validating.
        """
        if template_name in self._validating_dynamic:
            return True
        return False

    def is_dynamic_template_validated(self, template_name):
        """Is template already validated.

        Returns:
            bool: Is template validated.
        """

        if template_name in self._validated_dynamic:
            return True
        return False

    @contextlib.contextmanager
    def validating_dynamic(self, template_name):
        """Template name is validating and validated.

        Context manager that cares about storing template name validations of
        template.

        This is to avoid infinite loop of dynamic children validation.
        """
        self._validating_dynamic.add(template_name)
        try:
            yield
            self._validated_dynamic.add(template_name)

        finally:
            self._validating_dynamic.remove(template_name)

    def get_schema(self, schema_name):
        """Get schema definition data by it's name.

        Returns:
            dict: Copy of schema loaded from json files.

        Raises:
            KeyError: When schema name is stored in loaded templates or json
                file was not possible to parse or when schema name was not
                found.
        """
        if schema_name not in self._loaded_schemas:
            if schema_name in self._loaded_templates:
                raise KeyError((
                    "Template \"{}\" is used as `schema`"
                ).format(schema_name))

            elif schema_name in self._crashed_on_load:
                crashed_item = self._crashed_on_load[schema_name]
                raise KeyError(
                    "Unable to parse schema file \"{}\". {}".format(
                        crashed_item["filepath"], crashed_item["message"]
                    )
                )

            raise KeyError(
                "Schema \"{}\" was not found".format(schema_name)
            )
        return copy.deepcopy(self._loaded_schemas[schema_name])

    def get_template(self, template_name):
        """Get template definition data by it's name.

        Returns:
            list: Copy of template items loaded from json files.

        Raises:
            KeyError: When template name is stored in loaded schemas or json
                file was not possible to parse or when template name was not
                found.
        """
        if template_name not in self._loaded_templates:
            if template_name in self._loaded_schemas:
                raise KeyError((
                    "Schema \"{}\" is used as `template`"
                ).format(template_name))

            elif template_name in self._crashed_on_load:
                crashed_item = self._crashed_on_load[template_name]
                raise KeyError(
                    "Unable to parse template file \"{}\". {}".format(
                        crashed_item["filepath"], crashed_item["message"]
                    )
                )

            raise KeyError(
                "Template \"{}\" was not found".format(template_name)
            )
        return copy.deepcopy(self._loaded_templates[template_name])

    def resolve_schema_data(self, schema_data):
        """Resolve single item schema data as few types can be expanded.

        This is mainly for 'schema' and 'template' types. Type 'schema' does
        not have entity representation and 'template' may contain more than one
        output schemas.

        In other cases is retuned passed schema item in list.

        Goal is to have schema and template resolving at one place.

        Returns:
            list: Resolved schema data.
        """
        schema_type = schema_data["type"]
        if schema_type not in SCHEMA_EXTEND_TYPES:
            return [schema_data]

        if schema_type == "schema":
            return self.resolve_schema_data(
                self.get_schema(schema_data["name"])
            )

        if schema_type == "dynamic_schema":
            return self.resolve_dynamic_schema(schema_data["name"])

        template_name = schema_data["name"]
        template_def = self.get_template(template_name)

        filled_template = self._fill_template(
            schema_data, template_def
        )
        return filled_template

    def create_schema_object(self, schema_data, *args, **kwargs):
        """Create entity for passed schema data.

        Args:
            schema_data(dict): Schema definition of settings entity.

        Returns:
            ItemEntity: Created entity for passed schema data item.

        Raises:
            ValueError: When 'schema', 'template' or any of wrapper types are
                passed.
            KeyError: When type of passed schema is not known.
        """
        schema_type = schema_data["type"]
        if schema_type in ("schema", "template", "schema_template"):
            raise ValueError(
                "Got unresolved schema data of type \"{}\"".format(schema_type)
            )

        if schema_type in WRAPPER_TYPES:
            raise ValueError((
                "Function `create_schema_object` can't create entities"
                " of any wrapper type. Got type: \"{}\""
            ).format(schema_type))

        klass = self._loaded_types.get(schema_type)
        if not klass:
            raise KeyError("Unknown type \"{}\"".format(schema_type))

        return klass(schema_data, *args, **kwargs)

    def _load_types(self):
        """Prepare entity types for cretion of their objects.

        Currently all classes in `openpype.settings.entities` that inherited
        from `BaseEntity` are stored as loaded types. GUI types are stored to
        separated attribute to not mess up api access of entities.

        TODOs:
            Add more dynamic way how to add custom types from anywhere and
            better handling of abstract classes. Skipping them is dangerous.
        """

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

    def _load_schemas(self):
        """Load schema definitions from json files."""

        # Refresh all affecting variables
        self._crashed_on_load = {}
        self._loaded_templates = {}
        self._loaded_schemas = {}
        self._dynamic_schemas_by_id = {}

        dirpath = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "schemas",
            self.schema_type
        )
        loaded_schemas = {}
        loaded_templates = {}
        dynamic_schemas_by_id = {}
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
                        crashed_item["filepath"],
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

        defs_iter = self._dynamic_schemas_defs_by_id.items()
        for def_id, module_settings_def in defs_iter:
            dynamic_schemas_by_id[def_id] = (
                module_settings_def.get_dynamic_schemas(self.schema_type)
            )
            module_schemas = module_settings_def.get_settings_schemas(
                self.schema_type
            )
            for key, schema_data in module_schemas.items():
                if isinstance(schema_data, list):
                    if key in loaded_templates:
                        raise KeyError(
                            "Duplicated template key \"{}\"".format(key)
                        )
                    loaded_templates[key] = schema_data
                else:
                    if key in loaded_schemas:
                        raise KeyError(
                            "Duplicated schema key \"{}\"".format(key)
                        )
                    loaded_schemas[key] = schema_data

        self._loaded_templates = loaded_templates
        self._loaded_schemas = loaded_schemas
        self._dynamic_schemas_by_id = dynamic_schemas_by_id

    def get_dynamic_modules_settings_defs(self, schema_def_id):
        return self._dynamic_schemas_defs_by_id.get(schema_def_id)

    def _fill_template(self, child_data, template_def):
        """Fill template based on schema definition and template definition.

        Based on `child_data` is `template_def` modified and result is
        returned.

        Template definition may have defined data to fill which
        should be filled with data from child data.

        Child data may contain more than one output definition of an template.

        Child data can define paths to skip. Path is full path of an item
        which won't be returned.

        TODO:
        Be able to handle wrapper items here.

        Args:
            child_data(dict): Schema data of template item.
            template_def(dict): Template definition that will be filled with
                child_data.

        Returns:
            list: Resolved template always returns list of schemas.
        """
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
                output.extend(self._fill_template_data(
                    template_def, single_template_data, skip_paths
                ))

            except SchemaTemplateMissingKeys as exc:
                raise SchemaTemplateMissingKeys(
                    exc.missing_keys, exc.required_keys, template_name
                )
        return output

    def _fill_template_data(
        self,
        template,
        template_data,
        skip_paths,
        required_keys=None,
        missing_keys=None
    ):
        """Fill template values with data from schema data.

        Template has more abilities than schemas. It is expected that template
        will be used at multiple places (but may not). Schema represents
        exactly one entity and it's children but template may represent more
        entities.

        Template can have "keys to fill" from their definition. Some key may be
        required and some may be optional because template has their default
        values defined.

        Template also have ability to "skip paths" which means to skip entities
        from it's content. A template can be used across multiple places with
        different requirements.

        Raises:
            SchemaTemplateMissingKeys: When fill data do not contain all
                required keys for template.
        """
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

                output_item = self._fill_template_data(
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
                output[key] = self._fill_template_data(
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
            full_replacement = False
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
                    full_replacement = True
                else:
                    # Only replace the key in string
                    template = template.replace(replacement_string, value)

            if not full_replacement:
                output = (
                    template
                    .replace("__dbcb__", "{")
                    .replace("__decb__", "}")
                )
            else:
                output = template

        else:
            output = template

        if first and missing_keys:
            raise SchemaTemplateMissingKeys(missing_keys, required_keys)

        return output

    def _pop_metadata_item(self, template_def):
        """Pop template metadata from template definition.

        Template metadata may define default values if are not passed from
        schema data.
        """

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


class DynamicSchemaValueCollector:
    # Map schema hub type to store keys
    schema_hub_type_map = {
        SCHEMA_KEY_SYSTEM_SETTINGS: SYSTEM_SETTINGS_KEY,
        SCHEMA_KEY_PROJECT_SETTINGS: PROJECT_SETTINGS_KEY
    }

    def __init__(self, schema_hub):
        self._schema_hub = schema_hub
        self._dynamic_entities = []

    def add_entity(self, entity):
        self._dynamic_entities.append(entity)

    def create_hierarchy(self):
        output = collections.defaultdict(dict)
        for entity in self._dynamic_entities:
            output[entity.dynamic_schema_id][entity.path] = (
                entity.settings_value()
            )
        return output

    def save_values(self):
        hierarchy = self.create_hierarchy()

        for schema_def_id, schema_def_value in hierarchy.items():
            schema_def = self._schema_hub.get_dynamic_modules_settings_defs(
                schema_def_id
            )
            top_key = self.schema_hub_type_map.get(
                self._schema_hub.schema_type
            )
            schema_def.save_defaults(top_key, schema_def_value)
