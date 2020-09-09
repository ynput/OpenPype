import os
import json
import logging
import copy

log = logging.getLogger(__name__)

# Metadata keys for work with studio and project overrides
OVERRIDEN_KEY = "__overriden_keys__"
# NOTE key popping not implemented yet
POP_KEY = "__pop_key__"

# Folder where studio overrides are stored
STUDIO_OVERRIDES_PATH = os.environ["PYPE_CONFIG"]

# File where studio's system overrides are stored
SYSTEM_CONFIGURATIONS_PATH = os.path.join(
    STUDIO_OVERRIDES_PATH, "system_configurations.json"
)

# File where studio's default project overrides are stored
PROJECT_CONFIGURATIONS_FILENAME = "project_configurations.json"
PROJECT_CONFIGURATIONS_PATH = os.path.join(
    STUDIO_OVERRIDES_PATH, PROJECT_CONFIGURATIONS_FILENAME
)

# Folder where studio's per project overrides are stored
STUDIO_PROJECT_OVERRIDES_PATH = os.path.join(
    STUDIO_OVERRIDES_PATH, "project_overrides"
)

# Variable where cache of default configurations are stored
_DEFAULT_CONFIGURATIONS = None


def default_configuration():
    global _DEFAULT_CONFIGURATIONS
    if _DEFAULT_CONFIGURATIONS is None:
        current_dir = os.path.dirname(__file__)
        defaults_path = os.path.join(current_dir, "defaults")
        _DEFAULT_CONFIGURATIONS = load_jsons_from_dir(defaults_path)
    return _DEFAULT_CONFIGURATIONS


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

    if extra_comma:
        log.error("Extra comma in json file: \"{}\"".format(fpath))

    # return empty dict if file is empty
    if standard_json == "":
        return {}

    # Try to parse string
    try:
        return json.loads(standard_json)

    except json.decoder.JSONDecodeError:
        # Return empty dict if it is first time that decode error happened
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


def studio_system_configurations():
    if os.path.exists(SYSTEM_CONFIGURATIONS_PATH):
        return load_json(SYSTEM_CONFIGURATIONS_PATH)
    return {}


def studio_project_configurations():
    if os.path.exists(PROJECT_CONFIGURATIONS_PATH):
        return load_json(PROJECT_CONFIGURATIONS_PATH)
    return {}


def path_to_project_overrides(project_name):
    return os.path.join(
        STUDIO_PROJECT_OVERRIDES_PATH,
        project_name,
        PROJECT_CONFIGURATIONS_FILENAME
    )


def project_configurations_overrides(project_name):
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
