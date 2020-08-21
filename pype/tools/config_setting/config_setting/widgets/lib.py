import os
import json
import copy
from pype.api import config

OVERRIDEN_KEY = config.OVERRIDEN_KEY


# Singleton database of available inputs
class TypeToKlass:
    types = {}


NOT_SET = type("NOT_SET", (), {})
AS_WIDGET = type("AS_WIDGET", (), {})
METADATA_KEY = type("METADATA_KEY", (), {})
OVERRIDE_VERSION = 1


def convert_gui_data_to_overrides(data, first=True):
    if not data or not isinstance(data, dict):
        return data

    output = {}
    if first:
        output["__override_version__"] = OVERRIDE_VERSION

    if METADATA_KEY in data:
        metadata = data.pop(METADATA_KEY)
        for key, value in metadata.items():
            if key == "groups":
                output[OVERRIDEN_KEY] = value
            else:
                KeyError("Unknown metadata key \"{}\"".format(key))

    for key, value in data.items():
        output[key] = convert_gui_data_to_overrides(value, False)
    return output


def convert_overrides_to_gui_data(data, first=True):
    if not data or not isinstance(data, dict):
        return data

    output = {}
    if OVERRIDEN_KEY in data:
        groups = data.pop(OVERRIDEN_KEY)
        if METADATA_KEY not in output:
            output[METADATA_KEY] = {}
        output[METADATA_KEY]["groups"] = groups

    for key, value in data.items():
        output[key] = convert_overrides_to_gui_data(value, False)

    return output


def replace_inner_schemas(schema_data, schema_collection):
    if schema_data["type"] == "schema":
        raise ValueError("First item in schema data can't be schema.")

    children = schema_data.get("children")
    if not children:
        return schema_data

    new_children = []
    for child in children:
        if child["type"] != "schema":
            new_child = replace_inner_schemas(child, schema_collection)
            new_children.append(new_child)
            continue

        for schema_name in child["children"]:
            new_child = replace_inner_schemas(
                schema_collection[schema_name],
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


def file_keys_from_schema(schema_data):
    output = []
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


def validate_schema(schema_data):
    # TODO validator for key uniquenes
    # TODO validator that is_group key is not before is_file child
    # TODO validator that is_group or is_file is not on child without key
    validate_all_has_ending_file(schema_data)


def gui_schema(subfolder, main_schema_name):
    subfolder, main_schema_name
    dirpath = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "config_gui_schema",
        subfolder
    )

    loaded_schemas = {}
    for filename in os.listdir(dirpath):
        basename, ext = os.path.splitext(filename)
        if ext != ".json":
            continue

        filepath = os.path.join(dirpath, filename)
        with open(filepath, "r") as json_stream:
            schema_data = json.load(json_stream)
        loaded_schemas[basename] = schema_data

    main_schema = replace_inner_schemas(
        loaded_schemas[main_schema_name],
        loaded_schemas
    )
    validate_schema(main_schema)
    return main_schema
