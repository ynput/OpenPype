# -*- coding: utf-8 -*-
"""Get configuration data."""
import os
import json
import datetime
from .log import PypeLogger

log = PypeLogger().get_logger(__name__)


def get_datetime_data(datetime_obj=None):
    """Returns current datetime data as dictionary.

    Args:
        datetime_obj (datetime): Specific datetime object

    Returns:
        dict: prepared date & time data

    Available keys:
        "d" - <Day of month number> in shortest possible way.
        "dd" - <Day of month number> with 2 digits.
        "ddd" - <Week day name> shortened week day. e.g.: `Mon`, ...
        "dddd" - <Week day name> full name of week day. e.g.: `Monday`, ...
        "m" - <Month number> in shortest possible way. e.g.: `1` if January
        "mm" - <Month number> with 2 digits.
        "mmm" - <Month name> shortened month name. e.g.: `Jan`, ...
        "mmmm" - <Month name> full month name. e.g.: `January`, ...
        "yy" - <Year number> shortened year. e.g.: `19`, `20`, ...
        "yyyy" - <Year number> full year. e.g.: `2019`, `2020`, ...
        "H" - <Hours number 24-hour> shortened hours.
        "HH" - <Hours number 24-hour> with 2 digits.
        "h" - <Hours number 12-hour> shortened hours.
        "hh" - <Hours number 12-hour> with 2 digits.
        "ht" - <Midday type> AM or PM.
        "M" - <Minutes number> shortened minutes.
        "MM" - <Minutes number> with 2 digits.
        "S" - <Seconds number> shortened seconds.
        "SS" - <Seconds number> with 2 digits.
    """

    if not datetime_obj:
        datetime_obj = datetime.datetime.now()

    year = datetime_obj.strftime("%Y")

    month = datetime_obj.strftime("%m")
    month_name_full = datetime_obj.strftime("%B")
    month_name_short = datetime_obj.strftime("%b")
    day = datetime_obj.strftime("%d")

    weekday_full = datetime_obj.strftime("%A")
    weekday_short = datetime_obj.strftime("%a")

    hours = datetime_obj.strftime("%H")
    hours_midday = datetime_obj.strftime("%I")
    hour_midday_type = datetime_obj.strftime("%p")
    minutes = datetime_obj.strftime("%M")
    seconds = datetime_obj.strftime("%S")

    return {
        "d": str(int(day)),
        "dd": str(day),
        "ddd": weekday_short,
        "dddd": weekday_full,
        "m": str(int(month)),
        "mm": str(month),
        "mmm": month_name_short,
        "mmmm": month_name_full,
        "yy": str(year[2:]),
        "yyyy": str(year),
        "H": str(int(hours)),
        "HH": str(hours),
        "h": str(int(hours_midday)),
        "hh": str(hours_midday),
        "ht": hour_midday_type,
        "M": str(int(minutes)),
        "MM": str(minutes),
        "S": str(int(seconds)),
        "SS": str(seconds),
    }


def load_json(fpath, first_run=False):
    """Load JSON data.

    Args:
        fpath (str): Path to JSON file.
        first_run (bool): Flag to run checks if file is loaded for the first
                          time.
    Returns:
        dict: parsed JSON object.

    """
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


def collect_json_from_path(input_path, first_run=False):
    """Collect JSON file from path.

    Iterate through all subfolders and JSON files in `input_path`.

    Args:
        input_path (str): Path from JSONs will be collected.
        first_run (bool): Flag to run checks if file is loaded for the first
                          time.

    Returns:
        dict: Collected JSONs.

    Examples:

        Imagine path::
            `{input_path}/path/to/file.json`

        >>> collect_json_from_path(input_path)
        {'path':
            {'to':
                {'file': {JSON}
            }
        }

    """
    output = None
    if os.path.isdir(input_path):
        output = {}
        for file in os.listdir(input_path):
            full_path = os.path.sep.join([input_path, file])
            if os.path.isdir(full_path):
                loaded = collect_json_from_path(full_path, first_run)
                if loaded:
                    output[file] = loaded
            else:
                basename, ext = os.path.splitext(os.path.basename(file))
                if ext == '.json':
                    output[basename] = load_json(full_path, first_run)
    else:
        basename, ext = os.path.splitext(os.path.basename(input_path))
        if ext == '.json':
            output = load_json(input_path, first_run)

    return output


def get_presets(project=None, first_run=False):
    """Loads preset files with usage of ``collect_json_from_path``.

    Default preset path is set to: `{PYPE_CONFIG}/presets`
    Project preset path is set to: `{PYPE_PROJECT_CONFIGS}/project_name`

    Environment variable `PYPE_STUDIO_CONFIG` is required
    `PYPE_STUDIO_CONFIGS` only if want to use overrides per project.

    Args:
        project (str): Project name.
        first_run (bool): Flag to run checks if file is loaded for the first
                          time.

    Returns:
        None: If default path does not exist.
        default presets (dict): If project_name is not set or
                                if project's presets folder does not exist.
        project presets (dict): If project_name is set and include
                                override data.

    """
    # config_path should be set from environments?
    config_path = os.path.normpath(os.environ['PYPE_CONFIG'])
    preset_items = [config_path, 'presets']
    config_path = os.path.sep.join(preset_items)
    if not os.path.isdir(config_path):
        log.error('Preset path was not found: "{}"'.format(config_path))
        return None
    default_data = collect_json_from_path(config_path, first_run)

    if not project:
        project = os.environ.get('AVALON_PROJECT', None)

    if not project:
        return default_data

    project_configs_path = os.environ.get('PYPE_PROJECT_CONFIGS')
    if not project_configs_path:
        return default_data

    project_configs_path = os.path.normpath(project_configs_path)
    project_config_items = [project_configs_path, project, 'presets']
    project_config_path = os.path.sep.join(project_config_items)

    if not os.path.isdir(project_config_path):
        log.warning('Preset path for project {} not found: "{}"'.format(
            project, project_config_path
        ))
        return default_data
    project_data = collect_json_from_path(project_config_path, first_run)

    return update_dict(default_data, project_data)


def get_init_presets(project=None):
    """Loads content of presets.

    Llike :func:`get_presets()`` but also evaluate `init.json`
    pointer to default presets.

    Args:
        project(str): Project name.

    Returns:
        None: If default path does not exist
        default presets (dict): If project_name is not set or if project's
                                presets folder does not exist.
        project presets (dict): If project_name is set and include
                                override data.
    """
    presets = get_presets(project)

    try:
        # try if it is not in projects custom directory
        # `{PYPE_PROJECT_CONFIGS}/[PROJECT_NAME]/init.json`
        # init.json define preset names to be used
        p_init = presets["init"]
        presets["colorspace"] = presets["colorspace"][p_init["colorspace"]]
        presets["dataflow"] = presets["dataflow"][p_init["dataflow"]]
    except KeyError:
        log.warning("No projects custom preset available...")
        presets["colorspace"] = presets["colorspace"]["default"]
        presets["dataflow"] = presets["dataflow"]["default"]
        log.info(("Presets `colorspace` and `dataflow` "
                  "loaded from `default`..."))

    return presets


def update_dict(main_dict, enhance_dict):
    """Merges dictionaries by keys.

    Function call itself if value on key is again dictionary.

    Args:
        main_dict (dict): First dict to merge second one into.
        enhance_dict (dict): Second dict to be merged.

    Returns:
        dict: Merged result.

    .. note:: does not overrides whole value on first found key
              but only values differences from enhance_dict

    """
    for key, value in enhance_dict.items():
        if key not in main_dict:
            main_dict[key] = value
        elif isinstance(value, dict) and isinstance(main_dict[key], dict):
            main_dict[key] = update_dict(main_dict[key], value)
        else:
            main_dict[key] = value
    return main_dict
