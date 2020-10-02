import os
import json
import logging
import copy

log = logging.getLogger(__name__)

# Metadata keys for work with studio and project overrides
M_OVERRIDEN_KEY = "__overriden_keys__"
# Metadata key for storing information about environments
M_ENVIRONMENT_KEY = "__environment_keys__"
# NOTE key popping not implemented yet
M_POP_KEY = "__pop_key__"

# Folder where studio overrides are stored
STUDIO_OVERRIDES_PATH = os.environ["PYPE_PROJECT_CONFIGS"]

# File where studio's system overrides are stored
SYSTEM_SETTINGS_KEY = "system_settings"
SYSTEM_SETTINGS_PATH = os.path.join(
    STUDIO_OVERRIDES_PATH, SYSTEM_SETTINGS_KEY + ".json"
)

# File where studio's environment overrides are stored
ENVIRONMENTS_KEY = "environments"
ENVIRONMENTS_PATH = os.path.join(
    STUDIO_OVERRIDES_PATH, ENVIRONMENTS_KEY + ".json"
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


class DuplicatedEnvGroups(Exception):
    def __init__(self, duplicated):
        self.origin_duplicated = duplicated
        self.duplicated = {}
        for key, items in duplicated.items():
            self.duplicated[key] = []
            for item in items:
                self.duplicated[key].append("/".join(item["parents"]))

        msg = "Duplicated environment group keys. {}".format(
            ", ".join([
                "\"{}\"".format(env_key) for env_key in self.duplicated.keys()
            ])
        )

        super(DuplicatedEnvGroups, self).__init__(msg)


def reset_default_settings():
    global _DEFAULT_SETTINGS
    _DEFAULT_SETTINGS = None


def default_settings():
    global _DEFAULT_SETTINGS
    if _DEFAULT_SETTINGS is None:
        _DEFAULT_SETTINGS = load_jsons_from_dir(DEFAULTS_DIR)
    return copy.deepcopy(_DEFAULT_SETTINGS)


def load_json_file(fpath):
    # Load json data
    try:
        with open(fpath, "r") as opened_file:
            return json.load(opened_file)

    except json.decoder.JSONDecodeError:
        log.warning(
            "File has invalid json format \"{}\"".format(fpath),
            exc_info=True
        )

    return {}


def find_environments(data, with_items=False, parents=None):
    if not data or not isinstance(data, dict):
        return {}

    output = {}
    if parents is None:
        parents = []

    if M_ENVIRONMENT_KEY in data:
        metadata = data.get(M_ENVIRONMENT_KEY)
        for env_group_key, env_keys in metadata.items():
            if env_group_key not in output:
                output[env_group_key] = []

            _env_values = {}
            for key in env_keys:
                _env_values[key] = data[key]

            item = {
                "env": _env_values,
                "parents": parents[:-1]
            }
            output[env_group_key].append(item)

    for key, value in data.items():
        _parents = copy.deepcopy(parents)
        _parents.append(key)
        result = find_environments(value, True, _parents)
        if not result:
            continue

        for env_group_key, env_values in result.items():
            if env_group_key not in output:
                output[env_group_key] = []

            for env_values_item in env_values:
                output[env_group_key].append(env_values_item)

    if with_items:
        return output

    duplicated_env_groups = {}
    final_output = {}
    for key, value_in_list in output.items():
        if len(value_in_list) > 1:
            duplicated_env_groups[key] = value_in_list
        else:
            final_output[key] = value_in_list[0]["env"]

    if duplicated_env_groups:
        raise DuplicatedEnvGroups(duplicated_env_groups)
    return final_output


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


def studio_environments():
    if os.path.exists(ENVIRONMENTS_PATH):
        return load_json(ENVIRONMENTS_PATH)
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
    if M_OVERRIDEN_KEY in override_dict:
        overriden_keys = set(override_dict.pop(M_OVERRIDEN_KEY))
    else:
        overriden_keys = set()

    for key, value in override_dict.items():
        if value == M_POP_KEY:
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


def environments():
    # TODO remove these defaults (All should be set with system settings)
    envs = copy.deepcopy(default_settings()[ENVIRONMENTS_KEY])
    # This is part of loading environments from settings
    envs_from_system_settings = find_environments(system_settings())

    for env_group_key, values in envs_from_system_settings.items():
        envs[env_group_key] = values
    return envs
