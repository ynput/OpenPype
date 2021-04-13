import os
import sys
import json
import logging

ENV_KEY_MAPPING = {
    "PYPE_LOG_NO_COLORS": "OPENPYPE_LOG_NO_COLORS"
}
OBSOLETE_APP_GROUPS = (
    "premiere",
    "storyboardpro"
)

SKIP_ENV_KEYS = (
    # - Deprecated
    "PYPE_APP_ROOT",
    "PYPE_STUDIO_PLUGINS",
    "PYPE_PROJECT_PLUGINS",
    "PYPE_MODULE_ROOT",
    "PYPE_PROJECT_CONFIGS",
    "PYPE_PYTHON_EXE",
    "PYPE_SITE_PACKAGES",
    # - FFmpeg and OIIO should be installed and defined by us
    "FFMPEG_PATH",
    "PYPE_OIIO_PATH",
    # - DJV is set with settings
    "DJV_PATH",
    # - Is set on pype start automatically
    "PYBLISH_GUI",
    # - All PATH and PYTHONPATH modifications must be set again
    #   as previously set paths to Pype's repository can't be used anymore
    "PATH",
    "PYTHONPATH",

    # All pointing to different paths than expected (pype internal paths)
    "NUKE_PATH",
    "HIERO_PLUGIN_PATH",
    "HOUDINI_PATH",
    "HOUDINI_MENU_PATH",
    "BLENDER_USER_SCRIPTS",

    # Resolve
    "PRE_PYTHON_SCRIPT",

    # Deprecated key (used in avalon's launch system)
    "CREATE_NEW_CONSOLE"
)

# Add vendor modules to sys path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(CURRENT_DIR, "vendor"))

import yaml
from openpype.settings import lib
from openpype.settings import (
    SystemSettings,
    ProjectSettings
)
from openpype.settings.entities.exceptions import InvalidValueType

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
log = logging.getLogger("PresetsToSettings")


# --- Helper functions ---
def pjson(data):
    """Convert dictionary to string with indentation."""
    # For debugging
    return json.dumps(data, indent=4)


def load_yaml(filepath):
    """Load data from yaml file."""
    output = {}
    if filepath and os.path.exists(filepath):
        with open(filepath, "r") as file_stream:
            output = yaml.load(file_stream, Loader=yaml.FullLoader)
    return output


def get_path_values(data):
    if not data:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, str):
        return data.split(os.pathsep)
    if isinstance(data, dict):
        _data = get_platform_path_values(data)
        output = []
        for value in _data.values():
            output.extend(value)
        return output

    raise TypeError("Invalid type {} expected 'list', 'str' or 'dict'.".format(
        str(type(data))
    ))


def get_platform_path_values(data):
    platforms = {"windows", "linux", "darwin"}
    output = {
        platform: []
        for platform in platforms
    }
    if not data:
        pass

    elif isinstance(data, dict):
        for key, value in data.items():
            _key = key.lower()
            if _key not in platforms:
                log.warning((
                    "Key \"{}\" is not one of platform keys {}"
                ).format(_key, ", ".join(platforms)))
                continue
            output[key] = get_path_values(value)

    elif isinstance(data, (list, str)):
        _data = get_path_values(data)
        for platform in platforms:
            output[platform] = _data

    else:
        raise TypeError(
            "Invalid type {} expected 'list', 'str' or 'dict'.".format(
                str(type(data))
            )
        )
    return output
# -----------------------------------


def convert_environments(environments_data, system_settings):
    log.info("Converting environments to Settings")
    if not environments_data:
        log.info("Environments data are empty. Skipping")
        return

    modules_entity = system_settings["modules"]

    #  --- Deadline ---
    deadline_envs = environments_data.pop("deadline", {})
    deadline_rest_url = deadline_envs.get("DEADLINE_REST_URL")
    if deadline_rest_url:
        log.debug("Deadline rest url converted: {}".format(deadline_rest_url))
        modules_entity["deadline"]["DEADLINE_REST_URL"] = deadline_rest_url

    # --- Clockify ---
    clockify_envs = environments_data.pop("clockify", {})
    clockify_workspace = clockify_envs.get("CLOCKIFY_WORKSPACE")
    if clockify_workspace:
        log.debug(
            "Clockify workspace converted: {}".format(clockify_workspace)
        )
        modules_entity["clockify"]["workspace_name"] = clockify_workspace

    # --- Muster ---
    muster_envs = environments_data.pop("muster", {})
    muster_rest_url = muster_envs.get("MUSTER_REST_URL")
    if muster_rest_url:
        log.debug("Muster rest url converted: {}".format(muster_rest_url))
        modules_entity["muster"]["MUSTER_REST_URL"] = muster_rest_url

    # --- Avalon ---
    avalon_envs = environments_data.pop("avalon", {})
    # - avalon thumbnail root
    avalon_thumbnails_root = avalon_envs.get("AVALON_THUMBNAIL_ROOT")
    if avalon_thumbnails_root:
        try:
            per_platform = get_platform_path_values(avalon_thumbnails_root)
            log.debug("Avalon thumbnail root changed to: {}".format(
                pjson(per_platform)
            ))
            for platform, path_value in per_platform.items():
                if not path_value:
                    continue
                modules_entity["avalon"]["AVALON_THUMBNAIL_ROOT"][platform] = (
                    os.pathsep.join(path_value)
                )
        except Exception:
            log.warning(
                "Couldn't convert AVALON_THUMBNAIL_ROOT.", exc_info=True
            )

    # - avalon timeout
    avalon_timeout = avalon_envs.get("AVALON_TIMEOUT")
    if (
        avalon_timeout
        and int(avalon_timeout) != modules_entity["avalon"]["AVALON_TIMEOUT"]
    ):
        log.debug("Avalon timeout changed to {}".format(avalon_timeout))
        modules_entity["avalon"]["AVALON_TIMEOUT"] = int(avalon_timeout)

    # --- Ftrack ---
    ftrack_envs = environments_data.pop("ftrack", {})
    # - ftrack server
    ftrack_server = ftrack_envs.get("FTRACK_SERVER")
    if ftrack_server:
        log.debug("Ftrack server url set to \"{}\"".format(ftrack_server))
        modules_entity["ftrack"]["ftrack_server"] = ftrack_server

    # - user actions/events paths
    ftrack_user_path = []
    _ftrack_user_path = get_path_values(
        ftrack_envs.get("FTRACK_ACTIONS_PATH")
    )
    for path in _ftrack_user_path:
        if "/pype/modules/ftrack/actions" not in path.replace("\\", "/"):
            log.debug((
                "Ftrack additional user action/event path \"{}\""
            ).format(path))
            ftrack_user_path.append(path)

    if ftrack_user_path:
        modules_entity["ftrack"]["ftrack_actions_path"] = ftrack_user_path

    # - server actions/events paths
    ftrack_server_path = []
    _ftrack_server_path = get_path_values(
        ftrack_envs.get("FTRACK_EVENTS_PATH")
    )
    for path in _ftrack_server_path:
        if "/pype/modules/ftrack/events" not in path.replace("\\", "/"):
            log.debug((
                "Ftrack additional server action/event path \"{}\""
            ).format(path))
            ftrack_server_path.append(path)

    if ftrack_server_path:
        modules_entity["ftrack"]["ftrack_actions_path"] = ftrack_server_path

    # --- Global ---

    log.info("Converting global environments.")
    global_envs = environments_data.pop("global", {})

    # Studio name
    # <ENV KEY>: {
    #    default: <default value from pype-config>,
    #    mapping: <new key in settings (under general)>
    # }
    studio_name_keys_defaults = {
        "PYPE_STUDIO_NAME": {
            "default": "Studio Name",
            "mapping": "studio_name"
        },
        "PYPE_STUDIO_CODE": {
            "default": "stu",
            "mapping": "studio_code"
        }
    }
    for key in tuple(studio_name_keys_defaults.keys()):
        key_data = studio_name_keys_defaults[key]
        default_value = key_data["default"]
        map_key = key_data["mapping"]
        # Value from enviornments
        value = global_envs.pop(key, None)
        if not value or value == default_value:
            log.debug((
                "Studio key \"{}\" is not set or has default value. Skipping."
            ).format(map_key))
            continue
        log.debug("Studio key \"{}\" is set to \"{}\"".format(map_key, value))
        system_settings["general"][map_key] = value

    new_global_envs = {}
    for key, value in global_envs.items():
        if key not in SKIP_ENV_KEYS:
            new_global_envs[key] = value

    log.debug("New global environments value. {}".format(
        pjson(new_global_envs)
    ))
    system_settings["general"]["environment"] = new_global_envs

    # Applications
    # Obsolete
    for key in OBSOLETE_APP_GROUPS:
        if key in environments_data:
            environments_data.pop(key)
            log.info("Skipping obsolete application \"{}\"".format(key))

    # TODO add mapping of previous variant names -> new variant names
    apps_entity = system_settings["applications"]
    for app_group, app_entity in apps_entity.items():
        if "enabled" in app_entity and not app_entity["enabled"].value:
            log.info(
                "Skipping application group \"{}\". Not enabled.".format(
                    app_group
                )
            )
            continue

        # App environments
        if app_group in environments_data:
            _value = environments_data.pop(app_group)
            log.debug("App group \"{}\" - convering environments.".format(
                app_group
            ))

            env_values = app_entity["environment"].value
            for key, value in _value.items():
                # Skip if should be skipped
                if key in SKIP_ENV_KEYS:
                    continue

                # Map to new key
                elif key in ENV_KEY_MAPPING:
                    key = ENV_KEY_MAPPING[key]

                env_values[key] = value
            app_entity["environment"] = env_values

        else:
            log.debug("App group \"{}\" - didn't have environments.".format(
                app_group
            ))

        # Variant environments
        variants_entity = app_entity["variants"]
        is_dynamic = hasattr(variants_entity, "set_key_label")
        if not is_dynamic:
            for variant_name, variant_entity in variants_entity.items():
                full_name = "_".join((app_group, variant_name))
                if full_name not in environments_data:
                    continue

                if (
                    "enabled" in variant_entity
                    and not variant_entity["enabled"].value
                ):
                    log.info((
                        "Skipping application variant \"{}\". Not enabled."
                    ).format(full_name))
                    continue

                _value = environments_data.pop(full_name)
                log.debug((
                    "App variant \"{}\" - convering environments."
                ).format(full_name))
                env_values = variant_entity["environment"].value
                for key, value in _value.items():
                    # Skip if should be skipped
                    if key in SKIP_ENV_KEYS:
                        continue

                    # Map to new key
                    elif key in ENV_KEY_MAPPING:
                        key = ENV_KEY_MAPPING[key]

                    env_values[key] = value
                variant_entity["environment"] = env_values
        else:
            variant_start = "{}_".format(app_group)
            matching_keys = set()
            for env_key in environments_data.keys():
                if env_key.startswith(variant_start):
                    matching_keys.add(env_key)

            for env_key in matching_keys:
                variant_name = env_key[len(variant_start):].replace(".", "-")
                _value = environments_data.pop(env_key)

                variant_entity = variants_entity[variant_name]
                env_values = variant_entity["environment"].value
                for key, value in _value.items():
                    # Skip if should be skipped
                    if key in SKIP_ENV_KEYS:
                        continue

                    # Map to new key
                    elif key in ENV_KEY_MAPPING:
                        key = ENV_KEY_MAPPING[key]

                    env_values[key] = value
                variant_entity["environment"] = env_values

    # Cleanup of environments for app variant versions that are not available
    #   in Pype settings.
    for app_group in apps_entity.keys():
        for key in tuple(environments_data.keys()):
            if not key.startswith(app_group):
                continue

            _env_data = environments_data.pop(key)
            log.warning((
                "Environment data for Application variant \"{}\" are lost."
                " This version is not specified in Pype's settings."
                " Data: {}"
            ).format(key, pjson(_env_data)))

    # Tools
    tools_entity = system_settings["tools"]["tool_groups"]
    for key in tuple(environments_data.keys()):
        if "_" not in key:
            continue

        value = environments_data.pop(key)
        key_parts = key.split("_")
        group_key = key_parts.pop(0)
        variant_key = "_".join(key_parts).replace(".", "-")

        log.debug((
            "Converting environment key \"{}\""
            " into tool group \"{}\" and variant \"{}\"."
        ).format(key, group_key, variant_key))
        tools_entity[group_key]["variants"][variant_key] = value

    if not environments_data:
        return

    # - other tools
    log.info("Processing remaining environment keys.")
    for key, env_value in environments_data.items():
        if not key or not env_value:
            continue

        log.debug((
            "Environment group \"{}\" stored to same group as variant."
        ).format(key))

        tools_entity[key]["variants"][key] = env_value


def is_single_root(roots_data):
    """Check if passed roots data are single root or multiroot."""
    for value in roots_data.values():
        if isinstance(value, dict):
            return False
    return True


def _replace_root_key(root_key, new_root_key, templates_data):
    for value in templates_data.values():
        for template_key in tuple(value.keys()):
            template_value = value[template_key]
            if (
                isinstance(template_value, str)
                and root_key in template_value
            ):
                value[template_key] = template_value.replace(
                    root_key, new_root_key
                )


def _convert_anatomy_templates(templates_data, roots_converted):
    # Templates
    valid_default_keys = {
        "version_padding", "frame_padding", "version", "frame"
    }
    int_default_keys = {
        "version_padding", "frame_padding"
    }
    global_template_keys = {
        "work", "render", "publish", "hero", "delivery"
    }
    default_values = {}
    invalid_values = {}
    others_templates = {}
    # Template key `master` was renamed to `hero`
    if "master" in templates_data:
        master_values = templates_data.pop("master")
        hero_values = {}
        for key, value in master_values.items():
            hero_values[key] = value.replace("master", "hero")
        templates_data["hero"] = hero_values

    # Replace representation at the end of template value with `.{ext}`
    representation_ending = ".{representation}"
    ext_ending = "{ext}"
    ext_dot_ending = "." + ext_ending

    for key in tuple(templates_data.keys()):
        if isinstance(templates_data[key], dict):
            if key not in global_template_keys:
                others_templates[key] = templates_data.pop(key)
            continue

        value = templates_data.pop(key)
        if key not in valid_default_keys:
            invalid_values[key] = value
        elif key in int_default_keys:
            default_values[key] = int(value)
        else:
            default_values[key] = value

    for template_data in templates_data.values():
        if not isinstance(template_data, dict):
            continue

        for key in tuple(template_data.keys()):
            value = template_data[key]
            if not isinstance(value, str):
                continue

            # Check for ending of template and replace end of template value
            # with ".{ext}" if ends with ".{representation}"
            # or "{ext}" without dot
            ending_index = None
            if value.endswith(representation_ending):
                ending_index = len(value) - len(representation_ending)
            elif (
                value.endswith(ext_ending)
                and not value.endswith(ext_dot_ending)
            ):
                ending_index = len(value) - len(ext_ending)

            if ending_index is not None:
                template_data[key] = value[:ending_index] + ext_dot_ending

    if invalid_values:
        log.warning("Skipped anatomy templates default values.\n{}".format(
            pjson(invalid_values)
        ))

    # Modify `root` key in templates
    if roots_converted:
        root_key = "{root}"
        new_root_key = "{root[work]}"
        _replace_root_key(root_key, new_root_key, templates_data)
        _replace_root_key(root_key, new_root_key, others_templates)

    if default_values:
        templates_data["defaults"] = default_values
    if others_templates:
        templates_data["others"] = others_templates


def convert_global_anatomy(
    roots_data, templates_data, presets_data, project_settings
):
    # --- Roots ---
    roots_converted = False
    if roots_data:
        if is_single_root(roots_data):
            roots_converted = True
            roots_data = {"work": roots_data}

        anatomy_entity = project_settings["project_anatomy"]
        anatomy_entity["roots"] = roots_data

    # --- Templates ---
    if templates_data:
        _convert_anatomy_templates(templates_data, roots_converted)
        anatomy_entity["templates"] = templates_data

    # --- Project defaults ---
    presets_project_defaults = (
        presets_data
        .get("ftrack", {})
        .get("project_defaults") or {}
    )
    # Pop auto sync (not in attributes)
    presets_project_defaults.pop("avalon_auto_sync", None)

    # Pop task mapping and modify
    tasks_mapping = anatomy_entity["tasks"]
    task_mapping = presets_project_defaults.pop("task_short_names", None)
    for task_type, short_name in task_mapping.items():
        tasks_mapping[task_type] = {"short_name": short_name}

    attributes_entity = anatomy_entity["attributes"]

    for key, value in presets_project_defaults.items():
        if key not in attributes_entity:
            log.info(
                "Anatomy attributes does not contain key \"{}\"".format(key)
            )
            continue
        entity = attributes_entity[key]
        if key in ("applications", "tools_env"):
            if not isinstance(value, list):
                continue
            _value = []
            for _key in value:
                if _key in entity.enum_items:
                    _value.append(_key)
            value = _value
        entity.set(value)


def _convert_modules_data(presets, system_settings):
    if "tray" not in presets or "menu_items" not in presets["tray"]:
        return

    ignored_modules = {
        "Standalone Publish",
        "Avalon",
        "Rest Api",
        "Adobe Communicator",
        "Websocket Server",
        "Idle Manager"
    }
    attr_key_mapping = {
        "Clockify": "clockify",
        "Timers Manager": "timers_manager",
        "User settings": "user",
        "Ftrack": "ftrack",
        "Muster": "muster",
        "Logging": "log_viewer"
    }

    modules_entity = system_settings["modules"]

    menu_items = presets["tray"]["menu_items"] or {}
    items_usage = menu_items.get("item_usage") or {}
    for old_module_name, usage_value in items_usage.items():
        if not old_module_name or old_module_name in ignored_modules:
            continue
        module_name = attr_key_mapping.get(old_module_name)
        if module_name not in modules_entity:
            log.info((
                "Module not found in settings \"{}\". Can't change if enabled."
            ).format(old_module_name))
            continue

        module = modules_entity[module_name]
        if "enabled" in module:
            module["enabled"] = bool(usage_value)

    attributes = menu_items.get("attributes") or {}
    for old_module_name, module_attributes in attributes.items():
        if not old_module_name or old_module_name in ignored_modules:
            continue
        module_name = attr_key_mapping.get(old_module_name)
        if module_name not in modules_entity:
            log.info((
                "Module not found in settings \"{}\" Can't change attributes."
            ).format(module_name))
            continue

        module = modules_entity[module_name]
        if module_name == "Timers Manager":
            for attr_key in ("full_time", "message_time"):
                if attr_key not in module_attributes or attr_key not in module:
                    continue

                attr_value = module_attributes[attr_key]
                if attr_value is not None:
                    module[attr_key] = attr_value

        elif module_name == "Clockify":
            workspace_name = module_attributes.get("workspace_name")
            if workspace_name:
                module["workspace_name"] = workspace_name

    # Muster templates
    muster_templates_mapping = (
        presets
        .get("muster", {})
        .get("templates_mapping")
    )
    if muster_templates_mapping:
        log.debug("Converting muster templates mapping.")
        modules_entity["muster"]["templates_mapping"] = (
            muster_templates_mapping
        )

    # Ftrack intent
    intent_values = presets.get("global", {}).get("intent")
    if intent_values:
        ftrack_module = system_settings["modules"]["ftrack"]
        intent_items = {}
        for key, label in intent_values.get("items", {}).items():
            if key:
                intent_items[key] = label or key

        if intent_items:
            default_intent = intent_values.get("default")
            ftrack_module["intent"]["items"] = intent_items
            if default_intent in intent_items:
                ftrack_module["intent"]["default"] = default_intent


def _convert_applications_data(presets, system_settings):
    global_data = presets.get("global")
    if not global_data:
        return

    applications_data = global_data.get("applications")
    if not applications_data:
        return

    applications_entity = system_settings["applications"]
    for app_name, is_enabled in applications_data.items():
        if app_name in OBSOLETE_APP_GROUPS:
            continue

        if "_" not in app_name:
            log.info((
                "Skipped application with name \"{}\"."
                " Don't know how to convert."
            ).format(app_name))
            continue

        app_name_parts = app_name.split("_")
        group_name = app_name_parts.pop(0)
        if group_name in OBSOLETE_APP_GROUPS:
            continue

        variant_name = "_".join(app_name_parts).replace(".", "-")
        app_group_entity = applications_entity.get(group_name)
        if not app_group_entity:
            log.info(
                "Unknown Application group \"{}\". Skipping".format(group_name)
            )
            continue

        variants_entity = app_group_entity["variants"]
        is_dynamic = hasattr(variants_entity, "set_key_label")
        if is_dynamic:
            # Create variant - all that can be done
            _ = variants_entity[variant_name]
            continue

        variant_entity = variants_entity.get(variant_name)
        if not variant_entity:
            log.info("Application \"{}/{}\" was not found.".format(
                group_name, variant_name
            ))
            continue

        if "enabled" in variant_entity:
            variant_entity["enabled"] = bool(is_enabled)


def _convert_project_settings(presets, project_settings):
    # Ftrack settings
    project_settings_entity = project_settings["project_settings"]
    ftrack_entity = project_settings_entity["ftrack"]
    ftrack_presets = presets.get("ftrack") or {}

    ftrack_status_update = ftrack_presets.get("status_update")
    if ftrack_status_update:
        # Replace "_ignore_" with "__ignore__" and "_any_" with "__any__"
        if "_ignore_" in ftrack_status_update:
            ftrack_status_update["__ignore__"] = (
                ftrack_status_update.pop("_ignore_")
            )
        for key in tuple(ftrack_status_update.keys()):
            value = ftrack_status_update[key]
            if "_any_" in value:
                index = value.index("_any_")
                value.pop(index)
                value.insert(index, "__any__")
                ftrack_status_update[key] = value
        ftrack_entity["events"]["status_update"]["mapping"] = (
            ftrack_status_update
        )
    # status_version_to_task
    status_version_to_task = ftrack_presets.get("status_version_to_task")
    if status_version_to_task:
        new_value = {}
        for key, value in status_version_to_task.items():
            if not isinstance(value, list):
                value = [value]
            new_value[key] = value
        ftrack_entity["events"]["status_version_to_task"]["mapping"] = (
            new_value
        )

    # Harmony
    harmony_presets = presets.get("harmony")
    if harmony_presets:
        harmony_general_entity = project_settings_entity["harmony"]["general"]
        harmony_general = harmony_presets.get("general") or {}
        for key, value in harmony_general.items():
            if key in harmony_general_entity:
                harmony_general_entity[key] = value

    # Maya capture
    display_light_values = {
        0: "default",
        1: "all",
        2: "active",
        3: "flat",
        4: "none"
    }
    maya_publish_entity = project_settings_entity["maya"]["publish"]
    playblast_entity = (
        maya_publish_entity["ExtractPlayblast"]["capture_preset"]
    )
    maya_capture = presets.get("maya", {}).get("capture")
    if maya_capture:
        display_lights = (
            maya_capture
            .get("Viewport Options", {})
            .get("displayLights")
        )
        if display_lights is not None:
            # In presets were used indexes from `capture_gui` combobox
            #   instead of values. `display_light_values` represents list of
            #   the values.
            maya_capture["Viewport Options"]["displayLights"] = (
                display_light_values[int(display_lights)]
            )

        for category_name, category_data in maya_capture.items():
            if category_name not in playblast_entity:
                continue
            category_entity = playblast_entity[category_name]
            for key, value in category_data.items():
                if key in category_entity:
                    category_entity[key] = value

    # Plugins
    plugins_presets = presets.get("plugins")
    if not plugins_presets:
        log.info("Plugins presets are empty. Skipping.")
        return

    project_settings_entity = project_settings["project_settings"]
    for preset_key, preset_value in plugins_presets.items():
        preset_key_path = "/".join(["plugins", preset_key])
        if not preset_value:
            log.debug("Skipping empty value - {}".format(
                preset_key_path
            ))

        if not isinstance(preset_value, dict):
            log.warning((
                "Preset value has invalid type {} - {}"
            ).format(str(type(preset_value)), preset_key_path))
            continue

        if preset_key not in project_settings_entity:
            log.warning((
                "Presets plugin path not found in settings - {}"
            ).format(preset_key_path))
            continue

        entity = project_settings_entity[preset_key]
        for plugin_type, type_data in preset_value.items():
            plugin_type_path = "/".join([preset_key_path, plugin_type])
            if not type_data:
                log.debug("Skipping empty value - {}".format(
                    plugin_type_path
                ))
                continue

            # Key `filter` changed to `filters` (pyblish gui filtering)
            if plugin_type == "filter":
                plugin_type = "filters"

            if plugin_type not in entity:
                log.warning((
                    "Presets plugin path not found in settings - {}"
                ).format(plugin_type_path))
                continue

            # Key `workfile_build` is wrapped to `profiles` key in settings
            if plugin_type == "workfile_build":
                log.debug((
                    "Wrapping workfile build data in presets to 'profiles'"
                    " key - {}"
                ).format(plugin_type_path))
                type_data = {"profiles": type_data}

            if not isinstance(type_data, dict):
                continue

            plugin_type_entity = entity[plugin_type]
            for plugin_name, plugin_data in type_data.items():
                plugin_path = "/".join([plugin_type_path, plugin_name])
                if not plugin_data:
                    log.debug("Skipping empty value - {}".format(
                        plugin_path
                    ))
                    continue

                # Plugin `IntegrateMasterVersion` was renamed to
                #   `IntegrateHeroVersion`.
                if plugin_name == "IntegrateMasterVersion":
                    plugin_name = "IntegrateHeroVersion"

                if plugin_name not in plugin_type_entity:
                    # TODO log
                    continue

                if (
                    plugin_name == "profiles"
                    and plugin_type == "workfile_build"
                ):
                    plugin_type_entity[plugin_name] = plugin_data
                    continue

                if not isinstance(plugin_data, dict):
                    log.warning((
                        "Invalid value type {}. Value: {} - {}"
                    ).format(str(type(plugin_data)), plugin_data, plugin_path))
                    continue

                plugin_entity = plugin_type_entity[plugin_name]
                for key, value in plugin_data.items():
                    if key == "__documentation__":
                        continue

                    key_path = "/".join([plugin_path, key])
                    if key_path == (
                        "plugins/global/publish/ExtractBurnin/fields"
                    ):
                        continue

                    if (
                        plugin_path == "plugins/resolve/create/CreateShotClip"
                        and key == "steps"
                    ):
                        key = "countSteps"

                    if key not in plugin_entity:
                        log.warning((
                            "Missing plugin key \"{}\". Value: {} - {}"
                        ).format(key, value, plugin_path))
                        continue

                    # Pop `use_bg_color` from presets
                    if key_path == (
                        "plugins/global/publish/ExtractReview/profiles"
                    ):
                        new_value = []
                        for item in value:
                            if "outputs" in item:
                                for output_def in item["outputs"].values():
                                    output_def.pop("use_bg_color", None)
                            new_value.append(item)
                        value = new_value

                    try:
                        plugin_entity[key] = value
                    except InvalidValueType as exc:
                        log.error((
                            "{} - Failed value: {} - {}"
                        ).format(exc, value, key_path))
                    except Exception:
                        msg = (
                            "Unexpected error when converting value: {} - {}"
                        ).format(value, key_path)
                        log.error(msg, exc_info=True)


def convert_global_presets(
    presets,
    system_settings,
    project_settings
):
    _convert_modules_data(presets, system_settings)
    _convert_applications_data(presets, system_settings)
    _convert_project_settings(presets, project_settings)


def convert_presets_to_settings(
    system_settings, project_settings, pype_config_dir
):
    # Prepare data for presets and anatomy
    project_settings.change_project(None)
    templates_data = load_yaml(
        os.path.join(pype_config_dir, "anatomy", "default.yaml")
    )
    roots_data = lib.load_json_file(
        os.path.join(pype_config_dir, "anatomy", "roots.json")
    )
    presets_data = (
        lib.load_jsons_from_dir(os.path.join(pype_config_dir, "presets"))
    )

    convert_global_anatomy(
        roots_data,
        templates_data,
        presets_data,
        project_settings
    )
    convert_global_presets(
        presets_data,
        system_settings,
        project_settings
    )

    # Environments
    environments_dir = os.path.join(pype_config_dir, "environments")
    environments_data = lib.load_jsons_from_dir(environments_dir)

    convert_environments(environments_data, system_settings)


def main(config_dir):
    """Trigger function converting presets to settings.

    Args:
        cofing_dir (str): Path to pype-config directory from Pype 2.
            e.g. "Y:\pipeline\pype-production\pype-setup\repos\client-config"
    """

    system_settings = SystemSettings()
    project_settings = ProjectSettings()

    convert_presets_to_settings(
        system_settings,
        project_settings,
        config_dir
    )
    system_settings.save()
    project_settings.save()


if __name__ == "__main__":
    pype_config_dir = "D:/configs/pype-config"
    main(pype_config_dir)
