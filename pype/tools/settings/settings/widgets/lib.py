import os
import json
import copy
from pype.settings.lib import M_OVERRIDEN_KEY, M_ENVIRONMENT_KEY
from queue import Queue


# Singleton database of available inputs
class TypeToKlass:
    types = {}


NOT_SET = type("NOT_SET", (), {"__bool__": lambda obj: False})()
METADATA_KEY = type("METADATA_KEY", (), {})()
OVERRIDE_VERSION = 1
CHILD_OFFSET = 15


def convert_gui_data_with_metadata(data, ignored_keys=None):
    if not data or not isinstance(data, dict):
        return data

    if ignored_keys is None:
        ignored_keys = tuple()

    output = {}
    if METADATA_KEY in data:
        metadata = data.pop(METADATA_KEY)
        for key, value in metadata.items():
            if key in ignored_keys or key == "groups":
                continue

            if key == "environments":
                output[M_ENVIRONMENT_KEY] = value
            else:
                raise KeyError("Unknown metadata key \"{}\"".format(key))

    for key, value in data.items():
        output[key] = convert_gui_data_with_metadata(value, ignored_keys)
    return output


def convert_data_to_gui_data(data, first=True):
    if not data or not isinstance(data, dict):
        return data

    output = {}
    if M_ENVIRONMENT_KEY in data:
        data.pop(M_ENVIRONMENT_KEY)

    for key, value in data.items():
        output[key] = convert_data_to_gui_data(value, False)

    return output


def convert_gui_data_to_overrides(data, first=True):
    if not data or not isinstance(data, dict):
        return data

    output = {}
    if first:
        output["__override_version__"] = OVERRIDE_VERSION
        data = convert_gui_data_with_metadata(data)

    if METADATA_KEY in data:
        metadata = data.pop(METADATA_KEY)
        for key, value in metadata.items():
            if key == "groups":
                output[M_OVERRIDEN_KEY] = value
            else:
                raise KeyError("Unknown metadata key \"{}\"".format(key))

    for key, value in data.items():
        output[key] = convert_gui_data_to_overrides(value, False)
    return output


def convert_overrides_to_gui_data(data, first=True):
    if not data or not isinstance(data, dict):
        return data

    if first:
        data = convert_data_to_gui_data(data)

    output = {}
    if M_OVERRIDEN_KEY in data:
        groups = data.pop(M_OVERRIDEN_KEY)
        if METADATA_KEY not in output:
            output[METADATA_KEY] = {}
        output[METADATA_KEY]["groups"] = groups

    for key, value in data.items():
        output[key] = convert_overrides_to_gui_data(value, False)

    return output


def _fill_inner_schemas(schema_data, schema_collection):
    if schema_data["type"] == "schema":
        raise ValueError("First item in schema data can't be schema.")

    children = schema_data.get("children")
    if not children:
        return schema_data

    new_children = []
    for child in children:
        if child["type"] != "schema":
            new_child = _fill_inner_schemas(child, schema_collection)
            new_children.append(new_child)
            continue

        new_child = _fill_inner_schemas(
            schema_collection[child["name"]],
            schema_collection
        )
        new_children.append(new_child)

    schema_data["children"] = new_children
    return schema_data


class SchemaMissingFileInfo(Exception):
    def __init__(self, invalid):
        full_path_keys = []
        for item in invalid:
            full_path_keys.append("\"{}\"".format("/".join(item)))

        msg = (
            "Schema has missing definition of output file (\"is_file\" key)"
            " for keys. [{}]"
        ).format(", ".join(full_path_keys))
        super(SchemaMissingFileInfo, self).__init__(msg)


class SchemeGroupHierarchyBug(Exception):
    def __init__(self, invalid):
        full_path_keys = []
        for item in invalid:
            full_path_keys.append("\"{}\"".format("/".join(item)))

        msg = (
            "Items with attribute \"is_group\" can't have another item with"
            " \"is_group\" attribute as child. Error happened for keys: [{}]"
        ).format(", ".join(full_path_keys))
        super(SchemeGroupHierarchyBug, self).__init__(msg)


class SchemaDuplicatedKeys(Exception):
    def __init__(self, invalid):
        items = []
        for key_path, keys in invalid.items():
            joined_keys = ", ".join([
                "\"{}\"".format(key) for key in keys
            ])
            items.append("\"{}\" ({})".format(key_path, joined_keys))

        msg = (
            "Schema items contain duplicated keys in one hierarchy level. {}"
        ).format(" || ".join(items))
        super(SchemaDuplicatedKeys, self).__init__(msg)


class SchemaDuplicatedEnvGroupKeys(Exception):
    def __init__(self, invalid):
        items = []
        for key_path, keys in invalid.items():
            joined_keys = ", ".join([
                "\"{}\"".format(key) for key in keys
            ])
            items.append("\"{}\" ({})".format(key_path, joined_keys))

        msg = (
            "Schema items contain duplicated environment group keys. {}"
        ).format(" || ".join(items))
        super(SchemaDuplicatedEnvGroupKeys, self).__init__(msg)


def file_keys_from_schema(schema_data):
    output = []
    item_type = schema_data["type"]
    klass = TypeToKlass.types[item_type]
    if not klass.is_input_type:
        return output

    keys = []
    key = schema_data.get("key")
    if key:
        keys.append(key)

    for child in schema_data["children"]:
        if child.get("is_file"):
            _keys = copy.deepcopy(keys)
            _keys.append(child["key"])
            output.append(_keys)
            continue

        for result in file_keys_from_schema(child):
            _keys = copy.deepcopy(keys)
            _keys.extend(result)
            output.append(_keys)
    return output


def validate_all_has_ending_file(schema_data, is_top=True):
    item_type = schema_data["type"]
    klass = TypeToKlass.types[item_type]
    if not klass.is_input_type:
        return None

    if schema_data.get("is_file"):
        return None

    children = schema_data.get("children")
    if not children:
        return [[schema_data["key"]]]

    invalid = []
    keyless = "key" not in schema_data
    for child in children:
        result = validate_all_has_ending_file(child, False)
        if result is None:
            continue

        if keyless:
            invalid.extend(result)
        else:
            for item in result:
                new_invalid = [schema_data["key"]]
                new_invalid.extend(item)
                invalid.append(new_invalid)

    if not invalid:
        return None

    if not is_top:
        return invalid

    raise SchemaMissingFileInfo(invalid)


def validate_is_group_is_unique_in_hierarchy(
    schema_data, any_parent_is_group=False, keys=None
):
    is_top = keys is None
    if keys is None:
        keys = []

    keyless = "key" not in schema_data

    if not keyless:
        keys.append(schema_data["key"])

    invalid = []
    is_group = schema_data.get("is_group")
    if is_group and any_parent_is_group:
        invalid.append(copy.deepcopy(keys))

    if is_group:
        any_parent_is_group = is_group

    children = schema_data.get("children")
    if not children:
        return invalid

    for child in children:
        result = validate_is_group_is_unique_in_hierarchy(
            child, any_parent_is_group, copy.deepcopy(keys)
        )
        if not result:
            continue

        invalid.extend(result)

    if invalid and is_group and keys not in invalid:
        invalid.append(copy.deepcopy(keys))

    if not is_top:
        return invalid

    if invalid:
        raise SchemeGroupHierarchyBug(invalid)


def validate_keys_are_unique(schema_data, keys=None):
    children = schema_data.get("children")
    if not children:
        return

    is_top = keys is None
    if keys is None:
        keys = [schema_data["key"]]
    else:
        keys.append(schema_data["key"])

    child_queue = Queue()
    for child in children:
        child_queue.put(child)

    child_inputs = []
    while not child_queue.empty():
        child = child_queue.get()
        if "key" not in child:
            _children = child.get("children") or []
            for _child in _children:
                child_queue.put(_child)
        else:
            child_inputs.append(child)

    duplicated_keys = set()
    child_keys = set()
    for child in child_inputs:
        key = child["key"]
        if key in child_keys:
            duplicated_keys.add(key)
        else:
            child_keys.add(key)

    invalid = {}
    if duplicated_keys:
        joined_keys = "/".join(keys)
        invalid[joined_keys] = duplicated_keys

    for child in child_inputs:
        result = validate_keys_are_unique(child, copy.deepcopy(keys))
        if result:
            invalid.update(result)

    if not is_top:
        return invalid

    if invalid:
        raise SchemaDuplicatedKeys(invalid)


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
    validate_all_has_ending_file(schema_data)
    validate_is_group_is_unique_in_hierarchy(schema_data)
    validate_keys_are_unique(schema_data)
    validate_environment_groups_uniquenes(schema_data)


def gui_schema(subfolder, main_schema_name):
    subfolder, main_schema_name
    dirpath = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "gui_schemas",
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
                    raise Exception((
                        f"Unable to parse JSON file {filepath}\n{exc}"
                    )) from exc
            if isinstance(schema_data, list):
                loaded_schema_templates[basename] = schema_data
            else:
                loaded_schemas[basename] = schema_data

    main_schema = _fill_inner_schemas(
        loaded_schemas[main_schema_name],
        loaded_schemas
    )
    validate_schema(main_schema)
    return main_schema
