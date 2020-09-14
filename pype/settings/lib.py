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
STUDIO_OVERRIDES_PATH = os.environ["PYPE_PROJECT_CONFIGS"]

# File where studio's system overrides are stored
SYSTEM_SETTINGS_KEY = "system_settings"
SYSTEM_SETTINGS_PATH = os.path.join(
    STUDIO_OVERRIDES_PATH, SYSTEM_SETTINGS_KEY + ".json"
)

# File where studio's default project overrides are stored
PROJECT_SETTINGS_KEY = "project_settings"
PROJECT_SETTINGS_FILENAME = PROJECT_SETTINGS_KEY + ".json"
PROJECT_SETTINGS_PATH = os.path.join(
    STUDIO_OVERRIDES_PATH, PROJECT_SETTINGS_FILENAME
)

PROJECT_ANATOMY_KEY = "project_anatomy"
PROJECT_ANATOMY_FILENAME = PROJECT_ANATOMY_KEY + ".json"
PROJECT_ANATOMY_PATH = os.path.join(
    STUDIO_OVERRIDES_PATH, PROJECT_ANATOMY_FILENAME
)

# Path to default settings
DEFAULTS_DIR = os.path.join(os.path.dirname(__file__), "defaults")

# Variable where cache of default settings are stored
_DEFAULT_SETTINGS = None


def reset_default_settings():
    global _DEFAULT_SETTINGS
    _DEFAULT_SETTINGS = None


def default_settings():
    global _DEFAULT_SETTINGS
    if _DEFAULT_SETTINGS is None:
        _DEFAULT_SETTINGS = load_jsons_from_dir(DEFAULTS_DIR)
    return _DEFAULT_SETTINGS


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


def studio_system_settings():
    if os.path.exists(SYSTEM_SETTINGS_PATH):
        return load_json(SYSTEM_SETTINGS_PATH)
    return {}


def studio_project_settings():
    if os.path.exists(PROJECT_SETTINGS_PATH):
        return load_json(PROJECT_SETTINGS_PATH)
    return {}


def studio_project_anatomy():
    if os.path.exists(PROJECT_ANATOMY_PATH):
        return load_json(PROJECT_ANATOMY_PATH)
    return {}


def path_to_project_overrides(project_name):
    return os.path.join(
        STUDIO_OVERRIDES_PATH,
        project_name,
        PROJECT_SETTINGS_FILENAME
    )


def path_to_project_anatomy(project_name):
    return os.path.join(
        STUDIO_OVERRIDES_PATH,
        project_name,
        PROJECT_ANATOMY_FILENAME
    )


def project_settings_overrides(project_name):
    if not project_name:
        return {}

    path_to_json = path_to_project_overrides(project_name)
    if not os.path.exists(path_to_json):
        return {}
    return load_json(path_to_json)


def project_anatomy_overrides(project_name):
    if not project_name:
        return {}

    path_to_json = path_to_project_anatomy(project_name)
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


def apply_overrides(source_data, override_data):
    if not override_data:
        return source_data
    _source_data = copy.deepcopy(source_data)
    return merge_overrides(_source_data, override_data)


def system_settings():
    default_values = default_settings()[SYSTEM_SETTINGS_KEY]
    studio_values = studio_system_settings()
    return apply_overrides(default_values, studio_values)


def project_settings(project_name):
    default_values = default_settings()[PROJECT_SETTINGS_KEY]
    studio_values = studio_project_settings()

    studio_overrides = apply_overrides(default_values, studio_values)

    project_overrides = project_settings_overrides(project_name)

    return apply_overrides(studio_overrides, project_overrides)
