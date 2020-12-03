import os
import json
import logging
import copy

log = logging.getLogger(__name__)

# Py2 + Py3 json decode exception
JSON_EXC = getattr(json.decoder, "JSONDecodeError", ValueError)

# Metadata keys for work with studio and project overrides
M_OVERRIDEN_KEY = "__overriden_keys__"
# Metadata key for storing information about environments
M_ENVIRONMENT_KEY = "__environment_keys__"
# Metadata key for storing dynamic created labels
M_DYNAMIC_KEY_LABEL = "__dynamic_keys_labels__"
# NOTE key popping not implemented yet
M_POP_KEY = "__pop_key__"

# Folder where studio overrides are stored
STUDIO_OVERRIDES_PATH = os.getenv("PYPE_PROJECT_CONFIGS") or ""

# File where studio's system overrides are stored
SYSTEM_SETTINGS_KEY = "system_settings"
SYSTEM_SETTINGS_PATH = os.path.join(
    STUDIO_OVERRIDES_PATH, SYSTEM_SETTINGS_KEY + ".json"
)

# File where studio's environment overrides are stored
ENVIRONMENTS_KEY = "environments"

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


def get_default_settings():
    global _DEFAULT_SETTINGS
    if _DEFAULT_SETTINGS is None:
        _DEFAULT_SETTINGS = load_jsons_from_dir(DEFAULTS_DIR)
    return copy.deepcopy(_DEFAULT_SETTINGS)


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


def path_to_project_settings(project_name):
    if not project_name:
        return PROJECT_SETTINGS_PATH
    return os.path.join(
        STUDIO_OVERRIDES_PATH,
        project_name,
        PROJECT_SETTINGS_FILENAME
    )


def path_to_project_anatomy(project_name):
    if not project_name:
        return PROJECT_ANATOMY_PATH
    return os.path.join(
        STUDIO_OVERRIDES_PATH,
        project_name,
        PROJECT_ANATOMY_FILENAME
    )


def save_studio_settings(data):
    """Save studio overrides of system settings.

    Do not use to store whole system settings data with defaults but only it's
    overrides with metadata defining how overrides should be applied in load
    function. For loading should be used function `studio_system_settings`.

    Args:
        data(dict): Data of studio overrides with override metadata.
    """
    dirpath = os.path.dirname(SYSTEM_SETTINGS_PATH)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)

    print("Saving studio overrides. Output path: {}".format(
        SYSTEM_SETTINGS_PATH
    ))
    with open(SYSTEM_SETTINGS_PATH, "w") as file_stream:
        json.dump(data, file_stream, indent=4)


def save_project_settings(project_name, overrides):
    """Save studio overrides of project settings.

    Data are saved for specific project or as defaults for all projects.

    Do not use to store whole project settings data with defaults but only it's
    overrides with metadata defining how overrides should be applied in load
    function. For loading should be used function
    `get_studio_project_settings_overrides` for global project settings
    and `get_project_settings_overrides` for project specific settings.

    Args:
        project_name(str, null): Project name for which overrides are
            or None for global settings.
        data(dict): Data of project overrides with override metadata.
    """
    project_overrides_json_path = path_to_project_settings(project_name)
    dirpath = os.path.dirname(project_overrides_json_path)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)

    print("Saving overrides of project \"{}\". Output path: {}".format(
        project_name, project_overrides_json_path
    ))
    with open(project_overrides_json_path, "w") as file_stream:
        json.dump(overrides, file_stream, indent=4)


def save_project_anatomy(project_name, anatomy_data):
    """Save studio overrides of project anatomy data.

    Args:
        project_name(str, null): Project name for which overrides are
            or None for global settings.
        data(dict): Data of project overrides with override metadata.
    """
    project_anatomy_json_path = path_to_project_anatomy(project_name)
    dirpath = os.path.dirname(project_anatomy_json_path)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)

    print("Saving anatomy of project \"{}\". Output path: {}".format(
        project_name, project_anatomy_json_path
    ))
    with open(project_anatomy_json_path, "w") as file_stream:
        json.dump(anatomy_data, file_stream, indent=4)


def get_studio_system_settings_overrides():
    """Studio overrides of system settings."""
    if os.path.exists(SYSTEM_SETTINGS_PATH):
        return load_json_file(SYSTEM_SETTINGS_PATH)
    return {}


def get_studio_project_settings_overrides():
    """Studio overrides of default project settings."""
    if os.path.exists(PROJECT_SETTINGS_PATH):
        return load_json_file(PROJECT_SETTINGS_PATH)
    return {}


def get_studio_project_anatomy_overrides():
    """Studio overrides of default project anatomy data."""
    if os.path.exists(PROJECT_ANATOMY_PATH):
        return load_json_file(PROJECT_ANATOMY_PATH)
    return {}


def get_project_settings_overrides(project_name):
    """Studio overrides of project settings for specific project.

    Args:
        project_name(str): Name of project for which data should be loaded.

    Returns:
        dict: Only overrides for entered project, may be empty dictionary.
    """

    path_to_json = path_to_project_settings(project_name)
    if not os.path.exists(path_to_json):
        return {}
    return load_json_file(path_to_json)


def get_project_anatomy_overrides(project_name):
    """Studio overrides of project anatomy for specific project.

    Args:
        project_name(str): Name of project for which data should be loaded.

    Returns:
        dict: Only overrides for entered project, may be empty dictionary.
    """
    if not project_name:
        return {}

    path_to_json = path_to_project_anatomy(project_name)
    if not os.path.exists(path_to_json):
        return {}
    return load_json_file(path_to_json)


def merge_overrides(source_dict, override_dict):
    """Merge data from override_dict to source_dict."""

    if M_OVERRIDEN_KEY in override_dict:
        overriden_keys = set(override_dict.pop(M_OVERRIDEN_KEY))
    else:
        overriden_keys = set()

    for key, value in override_dict.items():
        if value == M_POP_KEY:
            source_dict.pop(key)

        elif (key in overriden_keys or key not in source_dict):
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


def get_system_settings():
    """System settings with applied studio overrides."""
    default_values = get_default_settings()[SYSTEM_SETTINGS_KEY]
    studio_values = get_studio_system_settings_overrides()
    return apply_overrides(default_values, studio_values)


def get_default_project_settings():
    """Project settings with applied studio's default project overrides."""
    default_values = get_default_settings()[PROJECT_SETTINGS_KEY]
    studio_values = get_studio_project_settings_overrides()

    return apply_overrides(default_values, studio_values)


def get_default_project_anatomy_data():
    """Project anatomy data with applied studio's default project overrides."""
    default_values = get_default_settings()[PROJECT_ANATOMY_KEY]
    studio_values = get_studio_project_anatomy_overrides()

    return apply_overrides(default_values, studio_values)


def get_anatomy_settings(project_name):
    """Project anatomy data with applied studio and project overrides."""
    if not project_name:
        raise ValueError(
            "Must enter project name."
            " Call `get_default_project_anatomy_data` to get project defaults."
        )

    studio_overrides = get_default_project_anatomy_data()
    project_overrides = get_project_anatomy_overrides(project_name)

    return apply_overrides(studio_overrides, project_overrides)


def get_project_settings(project_name):
    """Project settings with applied studio and project overrides."""
    if not project_name:
        raise ValueError(
            "Must enter project name."
            " Call `get_default_project_settings` to get project defaults."
        )

    studio_overrides = get_default_project_settings()
    project_overrides = get_project_settings_overrides(project_name)

    return apply_overrides(studio_overrides, project_overrides)


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

    return find_environments(get_system_settings())
