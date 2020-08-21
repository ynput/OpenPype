import os
import json
import logging
import copy

# DEBUG SETUP
os.environ["PYPE_CONFIG"] = os.path.dirname(os.path.dirname(__file__))
os.environ["PYPE_PROJECT_CONFIGS"] = os.path.join(
    os.environ["PYPE_CONFIG"], "config", "project_overrides"
)

log = logging.getLogger(__name__)

STUDIO_PRESETS_PATH = os.path.normpath(
    os.path.join(os.environ["PYPE_CONFIG"], "config", "studio_presets")
)
PROJECT_CONFIGURATION_DIR = "project_presets"
PROJECT_PRESETS_PATH = os.path.normpath(os.path.join(
    os.environ["PYPE_CONFIG"], "config", PROJECT_CONFIGURATION_DIR
))
first_run = False

# TODO key popping not implemented yet
POP_KEY = "__pop_key__"
OVERRIDEN_KEY = "__overriden_keys__"


def load_json(fpath):
    # Load json data
    with open(fpath, "r") as opened_file:
        lines = opened_file.read().splitlines()

    # prepare json string
    standard_json = ""
    for line in lines:
        # Remove all whitespace on both sides
        line = line.strip()

        # Skip blank lines
        if len(line) == 0:
            continue

        standard_json += line

    # Check if has extra commas
    extra_comma = False
    if ",]" in standard_json or ",}" in standard_json:
        extra_comma = True
    standard_json = standard_json.replace(",]", "]")
    standard_json = standard_json.replace(",}", "}")

    global first_run
    if extra_comma and first_run:
        log.error("Extra comma in json file: \"{}\"".format(fpath))

    # return empty dict if file is empty
    if standard_json == "":
        if first_run:
            log.error("Empty json file: \"{}\"".format(fpath))
        return {}

    # Try to parse string
    try:
        return json.loads(standard_json)

    except json.decoder.JSONDecodeError:
        # Return empty dict if it is first time that decode error happened
        if not first_run:
            return {}

    # Repreduce the exact same exception but traceback contains better
    # information about position of error in the loaded json
    try:
        with open(fpath, "r") as opened_file:
            json.load(opened_file)

    except json.decoder.JSONDecodeError:
        log.warning(
            "File has invalid json format \"{}\"".format(fpath),
            exc_info=True
        )

    return {}


def subkey_merge(_dict, value, keys):
    key = keys.pop(0)
    if not keys:
        _dict[key] = value
        return _dict

    if key not in _dict:
        _dict[key] = {}
    _dict[key] = subkey_merge(_dict[key], value, keys)

    return _dict


def load_jsons_from_dir(path, *args, **kwargs):
    output = {}

    path = os.path.normpath(path)
    if not os.path.exists(path):
        # TODO warning
        return output

    sub_keys = list(kwargs.pop("subkeys", args))
    for sub_key in tuple(sub_keys):
        _path = os.path.join(path, sub_key)
        if not os.path.exists(_path):
            break

        path = _path
        sub_keys.pop(0)

    base_len = len(path) + 1
    for base, _directories, filenames in os.walk(path):
        base_items_str = base[base_len:]
        if not base_items_str:
            base_items = []
        else:
            base_items = base_items_str.split(os.path.sep)

        for filename in filenames:
            basename, ext = os.path.splitext(filename)
            if ext == ".json":
                full_path = os.path.join(base, filename)
                value = load_json(full_path)
                dict_keys = base_items + [basename]
                output = subkey_merge(output, value, dict_keys)

    for sub_key in sub_keys:
        output = output[sub_key]
    return output


def studio_presets(*args, **kwargs):
    return load_jsons_from_dir(STUDIO_PRESETS_PATH, *args, **kwargs)


def global_project_presets(**kwargs):
    return load_jsons_from_dir(PROJECT_PRESETS_PATH, **kwargs)


def path_to_project_overrides(project_name):
    project_configs_path = os.environ["PYPE_PROJECT_CONFIGS"]
    dirpath = os.path.join(project_configs_path, project_name)
    return os.path.join(dirpath, PROJECT_CONFIGURATION_DIR + ".json")


def project_preset_overrides(project_name, **kwargs):
    if not project_name:
        return {}

    path_to_json = path_to_project_overrides(project_name)
    if not os.path.exists(path_to_json):
        return {}
    return load_json(path_to_json)


def merge_overrides(global_dict, override_dict):
    if OVERRIDEN_KEY in override_dict:
        overriden_keys = set(override_dict.pop(OVERRIDEN_KEY))
    else:
        overriden_keys = set()

    for key, value in override_dict.items():
        if value == POP_KEY:
            global_dict.pop(key)

        elif (
            key in overriden_keys
            or key not in global_dict
        ):
            global_dict[key] = value

        elif isinstance(value, dict) and isinstance(global_dict[key], dict):
            global_dict[key] = merge_overrides(global_dict[key], value)

        else:
            global_dict[key] = value
    return global_dict


def apply_overrides(global_presets, project_overrides):
    global_presets = copy.deepcopy(global_presets)
    if not project_overrides:
        return global_presets
    return merge_overrides(global_presets, project_overrides)


def project_presets(project_name=None, **kwargs):
    global_presets = global_project_presets(**kwargs)

    if not project_name:
        project_name = os.environ.get("AVALON_PROJECT")
    project_overrides = project_preset_overrides(project_name, **kwargs)

    return apply_overrides(global_presets, project_overrides)


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
