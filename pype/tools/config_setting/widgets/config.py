import os
import json
import logging
import copy

# DEBUG SETUP
os.environ["AVALON_PROJECT"] = "kuba_each_case"
os.environ["PYPE_PROJECT_CONFIGS"] = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "config",
    "project_overrides"
)
#

log = logging.getLogger(__name__)

config_path = os.path.dirname(os.path.dirname(__file__))
studio_presets_path = os.path.normpath(
    os.path.join(config_path, "config", "studio_presets")
)
project_presets_path = os.path.normpath(
    os.path.join(config_path, "config", "project_presets")
)
first_run = False

OVERRIDE_KEY = "__overriden__"
POP_KEY = "__popkey__"


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


def subkey_merge(_dict, value, keys, with_metadata=False):
    key = keys.pop(0)
    if not keys:
        if with_metadata:
            _dict[key] = {"type": "file", "value": value}
        else:
            _dict[key] = value
        return _dict

    if key not in _dict:
        if with_metadata:
            _dict[key] = {"type": "folder", "value": {}}
        else:
            _dict[key] = {}

    if with_metadata:
        sub_dict = _dict[key]["value"]
    else:
        sub_dict = _dict[key]

    _value = subkey_merge(sub_dict, value, keys, with_metadata)
    if with_metadata:
        _dict[key]["value"] = _value
    else:
        _dict[key] = _value
    return _dict


def load_jsons_from_dir(path, *args, **kwargs):
    output = {}

    path = os.path.normpath(path)
    if not os.path.exists(path):
        # TODO warning
        return output

    with_metadata = kwargs.get("with_metadata")
    sub_keys = list(kwargs.pop("subkeys", args))
    for sub_key in tuple(sub_keys):
        _path = os.path.join(path, sub_key)
        if not os.path.exists(_path):
            break

        path = _path
        sub_keys.pop(0)

    base_len = len(path) + 1
    ext_len = len(".json")

    for base, _directories, filenames in os.walk(path):
        for filename in filenames:
            basename, ext = os.path.splitext(filename)
            if ext == ".json":
                full_path = os.path.join(base, filename)
                value = load_json(full_path)

                # dict_path = os.path.join(base[base_len:], basename)
                # dict_keys = dict_path.split(os.path.sep)
                dict_keys = base[base_len:].split(os.path.sep) + [basename]
                output = subkey_merge(output, value, dict_keys, with_metadata)

    for sub_key in sub_keys:
        output = output[sub_key]
    return output


def studio_presets(*args, **kwargs):
    return load_jsons_from_dir(studio_presets_path, *args, **kwargs)


def global_project_presets(**kwargs):
    return load_jsons_from_dir(project_presets_path, **kwargs)


def studio_presets_with_metadata(*args, **kwargs):
    kwargs["with_metadata"] = True
    return load_jsons_from_dir(studio_presets_path, *args, **kwargs)


def global_project_presets_with_metadata(**kwargs):
    kwargs["with_metadata"] = True
    return load_jsons_from_dir(project_presets_path, **kwargs)


def project_preset_overrides(project_name, **kwargs):
    project_configs_path = os.environ.get("PYPE_PROJECT_CONFIGS")
    if project_name and project_configs_path:
        return load_jsons_from_dir(
            os.path.join(project_configs_path, project_name),
            **kwargs
        )
    return {}


def merge_overrides(global_dict, override_dict):
    if OVERRIDE_KEY in override_dict:
        _override = override_dict.pop(OVERRIDE_KEY)
        if _override:
            return override_dict

    for key, value in override_dict.items():
        if value == POP_KEY:
            global_dict.pop(key)

        elif key == OVERRIDE_KEY:
            continue

        elif key not in global_dict:
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
    return main_schema
