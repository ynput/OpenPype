import os
import json
import functools
import logging
import copy
from .constants import (
    M_OVERRIDEN_KEY,
    M_ENVIRONMENT_KEY,

    METADATA_KEYS,

    SYSTEM_SETTINGS_KEY,
    PROJECT_SETTINGS_KEY,
    PROJECT_ANATOMY_KEY
)

log = logging.getLogger(__name__)

# Py2 + Py3 json decode exception
JSON_EXC = getattr(json.decoder, "JSONDecodeError", ValueError)


# Path to default settings
DEFAULTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "defaults"
)

# Variable where cache of default settings are stored
_DEFAULT_SETTINGS = None

# Handler of studio overrides
_SETTINGS_HANDLER = None


def require_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        global _SETTINGS_HANDLER
        if _SETTINGS_HANDLER is None:
            _SETTINGS_HANDLER = create_settings_handler()
        return func(*args, **kwargs)
    return wrapper


def create_settings_handler():
    from .handlers import MongoSettingsHandler
    # Handler can't be created in global space on initialization but only when
    # needed. Plus here may be logic: Which handler is used (in future).
    return MongoSettingsHandler()


@require_handler
def save_studio_settings(data):
    return _SETTINGS_HANDLER.save_studio_settings(data)


@require_handler
def save_project_settings(project_name, overrides):
    return _SETTINGS_HANDLER.save_project_settings(project_name, overrides)


@require_handler
def save_project_anatomy(project_name, anatomy_data):
    return _SETTINGS_HANDLER.save_project_anatomy(project_name, anatomy_data)


@require_handler
def get_studio_system_settings_overrides():
    return _SETTINGS_HANDLER.get_studio_system_settings_overrides()


@require_handler
def get_studio_project_settings_overrides():
    return _SETTINGS_HANDLER.get_studio_project_settings_overrides()


@require_handler
def get_studio_project_anatomy_overrides():
    return _SETTINGS_HANDLER.get_studio_project_anatomy_overrides()


@require_handler
def get_project_settings_overrides(project_name):
    return _SETTINGS_HANDLER.get_project_settings_overrides(project_name)


@require_handler
def get_project_anatomy_overrides(project_name):
    return _SETTINGS_HANDLER.get_project_anatomy_overrides(project_name)


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


def get_default_settings():
    # TODO add cacher
    return load_jsons_from_dir(DEFAULTS_DIR)
    # global _DEFAULT_SETTINGS
    # if _DEFAULT_SETTINGS is None:
    #     _DEFAULT_SETTINGS = load_jsons_from_dir(DEFAULTS_DIR)
    # return copy.deepcopy(_DEFAULT_SETTINGS)


def load_json_file(fpath):
    # Load json data
    try:
        with open(fpath, "r") as opened_file:
            return json.load(opened_file)

    except JSON_EXC:
        log.warning(
            "File has invalid json format \"{}\"".format(fpath),
            exc_info=True
        )
    return {}


def load_jsons_from_dir(path, *args, **kwargs):
    """Load all .json files with content from entered folder path.

    Data are loaded recursively from a directory and recreate the
    hierarchy as a dictionary.

    Entered path hiearchy:
    |_ folder1
    | |_ data1.json
    |_ folder2
      |_ subfolder1
        |_ data2.json

    Will result in:
    ```javascript
    {
        "folder1": {
            "data1": "CONTENT OF FILE"
        },
        "folder2": {
            "data1": {
                "subfolder1": "CONTENT OF FILE"
            }
        }
    }
    ```

    Args:
        path (str): Path to the root folder where the json hierarchy starts.

    Returns:
        dict: Loaded data.
    """
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
                value = load_json_file(full_path)
                dict_keys = base_items + [basename]
                output = subkey_merge(output, value, dict_keys)

    for sub_key in sub_keys:
        output = output[sub_key]
    return output


def find_environments(data, with_items=False, parents=None):
    """ Find environemnt values from system settings by it's metadata.

    Args:
        data(dict): System settings data or dictionary which may contain
            environments metadata.

    Returns:
        dict: Key as Environment key and value for `acre` module.
    """
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


def merge_overrides(source_dict, override_dict):
    """Merge data from override_dict to source_dict."""

    if M_OVERRIDEN_KEY in override_dict:
        overriden_keys = set(override_dict.pop(M_OVERRIDEN_KEY))
    else:
        overriden_keys = set()

    for key, value in override_dict.items():
        if (key in overriden_keys or key not in source_dict):
            source_dict[key] = value

        elif isinstance(value, dict) and isinstance(source_dict[key], dict):
            source_dict[key] = merge_overrides(source_dict[key], value)

        else:
            source_dict[key] = value
    return source_dict


def apply_overrides(source_data, override_data):
    if not override_data:
        return source_data
    _source_data = copy.deepcopy(source_data)
    return merge_overrides(_source_data, override_data)


def get_system_settings(clear_metadata=True):
    """System settings with applied studio overrides."""
    default_values = get_default_settings()[SYSTEM_SETTINGS_KEY]
    studio_values = get_studio_system_settings_overrides()
    result = apply_overrides(default_values, studio_values)
    if clear_metadata:
        clear_metadata_from_settings(result)
    return result


def get_default_project_settings(clear_metadata=True):
    """Project settings with applied studio's default project overrides."""
    default_values = get_default_settings()[PROJECT_SETTINGS_KEY]
    studio_values = get_studio_project_settings_overrides()
    result = apply_overrides(default_values, studio_values)
    if clear_metadata:
        clear_metadata_from_settings(result)
    return result


def get_default_anatomy_settings(clear_metadata=True):
    """Project anatomy data with applied studio's default project overrides."""
    default_values = get_default_settings()[PROJECT_ANATOMY_KEY]
    studio_values = get_studio_project_anatomy_overrides()

    # TODO uncomment and remove hotfix result when overrides of anatomy
    #   are stored correctly.
    # result = apply_overrides(default_values, studio_values)
    result = copy.deepcopy(default_values)
    if studio_values:
        for key, value in studio_values.items():
            result[key] = value
    if clear_metadata:
        clear_metadata_from_settings(result)
    return result


def get_anatomy_settings(project_name, clear_metadata=True):
    """Project anatomy data with applied studio and project overrides."""
    if not project_name:
        raise ValueError(
            "Must enter project name. Call "
            "`get_default_anatomy_settings` to get project defaults."
        )

    studio_overrides = get_default_anatomy_settings(False)
    project_overrides = get_project_anatomy_overrides(
        project_name
    )

    # TODO uncomment and remove hotfix result when overrides of anatomy
    #   are stored correctly.
    # result = apply_overrides(studio_overrides, project_overrides)
    result = copy.deepcopy(studio_overrides)
    if project_overrides:
        for key, value in project_overrides.items():
            result[key] = value
    if clear_metadata:
        clear_metadata_from_settings(result)
    return result


def get_project_settings(project_name, clear_metadata=True):
    """Project settings with applied studio and project overrides."""
    if not project_name:
        raise ValueError(
            "Must enter project name."
            " Call `get_default_project_settings` to get project defaults."
        )

    studio_overrides = get_default_project_settings(False)
    project_overrides = get_project_settings_overrides(
        project_name
    )

    result = apply_overrides(studio_overrides, project_overrides)
    if clear_metadata:
        clear_metadata_from_settings(result)
    return result


def get_current_project_settings():
    """Project settings for current context project.

    Project name should be stored in environment variable `AVALON_PROJECT`.
    This function should be used only in host context where environment
    variable must be set and should not happen that any part of process will
    change the value of the enviornment variable.
    """
    project_name = os.environ.get("AVALON_PROJECT")
    if not project_name:
        raise ValueError(
            "Missing context project in environemt variable `AVALON_PROJECT`."
        )
    return get_project_settings(project_name)


def get_environments():
    """Calculated environment based on defaults and system settings.

    Any default environment also found in the system settings will be fully
    overriden by the one from the system settings.

    Returns:
        dict: Output should be ready for `acre` module.
    """

    return find_environments(get_system_settings(False))


def clear_metadata_from_settings(values):
    """Remove all metadata keys from loaded settings."""
    if isinstance(values, dict):
        for key in tuple(values.keys()):
            if key in METADATA_KEYS:
                values.pop(key)
            else:
                clear_metadata_from_settings(values[key])
    elif isinstance(values, list):
        for item in values:
            clear_metadata_from_settings(item)
