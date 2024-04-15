"""Helper functionality to convert AYON settings to OpenPype v3 settings.

The settings are converted, so we can use v3 code with AYON settings. Once
the code of and addon is converted to full AYON addon which expect AYON
settings the conversion function can be removed.

The conversion is hardcoded -> there is no other way how to achieve the result.

Main entrypoints are functions:
- convert_project_settings - convert settings to project settings
- convert_system_settings - convert settings to system settings
# Both getters cache values
- get_ayon_project_settings - replacement for 'get_project_settings'
- get_ayon_system_settings - replacement for 'get_system_settings'
"""
import os
import collections
import json
import copy
import time

import six

from openpype.client import get_ayon_server_api_connection


def _convert_color(color_value):
    if isinstance(color_value, six.string_types):
        color_value = color_value.lstrip("#")
        color_value_len = len(color_value)
        _color_value = []
        for idx in range(color_value_len // 2):
            _color_value.append(int(color_value[idx:idx + 2], 16))
        for _ in range(4 - len(_color_value)):
            _color_value.append(255)
        return _color_value

    if isinstance(color_value, list):
        # WARNING R,G,B can be 'int' or 'float'
        # - 'float' variant is using 'int' for min: 0 and max: 1
        if len(color_value) == 3:
            # Add alpha
            color_value.append(255)
        else:
            # Convert float alha to int
            alpha = int(color_value[3] * 255)
            if alpha > 255:
                alpha = 255
            elif alpha < 0:
                alpha = 0
            color_value[3] = alpha
    return color_value


def _convert_host_imageio(host_settings):
    if "imageio" not in host_settings:
        return

    # --- imageio ---
    ayon_imageio = host_settings["imageio"]
    # TODO remove when fixed on server
    if "ocio_config" in ayon_imageio["ocio_config"]:
        ayon_imageio["ocio_config"]["filepath"] = (
            ayon_imageio["ocio_config"].pop("ocio_config")
        )
    # Convert file rules
    imageio_file_rules = ayon_imageio["file_rules"]
    new_rules = {}
    for rule in imageio_file_rules["rules"]:
        name = rule.pop("name")
        new_rules[name] = rule
    imageio_file_rules["rules"] = new_rules


def _convert_applications_groups(groups, clear_metadata):
    environment_key = "environment"
    if isinstance(groups, dict):
        new_groups = []
        for name, item in groups.items():
            item["name"] = name
            new_groups.append(item)
        groups = new_groups

    output = {}
    group_dynamic_labels = {}
    for group in groups:
        group_name = group.pop("name")
        if "label" in group:
            group_dynamic_labels[group_name] = group["label"]

        tool_group_envs = group[environment_key]
        if isinstance(tool_group_envs, six.string_types):
            group[environment_key] = json.loads(tool_group_envs)

        variants = {}
        variant_dynamic_labels = {}
        for variant in group.pop("variants"):
            variant_name = variant.pop("name")
            label = variant.get("label")
            if label and label != variant_name:
                variant_dynamic_labels[variant_name] = label
            variant_envs = variant[environment_key]
            if isinstance(variant_envs, six.string_types):
                variant[environment_key] = json.loads(variant_envs)
            variants[variant_name] = variant
        group["variants"] = variants

        if not clear_metadata:
            variants["__dynamic_keys_labels__"] = variant_dynamic_labels
        output[group_name] = group

    if not clear_metadata:
        output["__dynamic_keys_labels__"] = group_dynamic_labels
    return output


def _convert_applications_system_settings(
    ayon_settings, output, clear_metadata
):
    # Addon settings
    addon_settings = ayon_settings["applications"]

    # Remove project settings
    addon_settings.pop("only_available", None)

    # Applications settings
    ayon_apps = addon_settings["applications"]

    additional_apps = ayon_apps.pop("additional_apps")
    applications = _convert_applications_groups(
        ayon_apps, clear_metadata
    )
    applications["additional_apps"] = _convert_applications_groups(
        additional_apps, clear_metadata
    )

    # Tools settings
    tools = _convert_applications_groups(
        addon_settings["tool_groups"], clear_metadata
    )

    output["applications"] = applications
    output["tools"] = {"tool_groups": tools}


def _convert_general(ayon_settings, output, default_settings):
    # TODO get studio name/code
    core_settings = ayon_settings["core"]
    environments = core_settings["environments"]
    if isinstance(environments, six.string_types):
        environments = json.loads(environments)

    general = default_settings["general"]
    general.update({
        "log_to_server": False,
        "studio_name": core_settings["studio_name"],
        "studio_code": core_settings["studio_code"],
        "environment": environments
    })
    output["general"] = general


def _convert_kitsu_system_settings(
    ayon_settings, output, addon_versions, default_settings
):
    enabled = addon_versions.get("kitsu") is not None
    kitsu_settings = default_settings["modules"]["kitsu"]
    kitsu_settings["enabled"] = enabled
    if enabled:
        kitsu_settings["server"] = ayon_settings["kitsu"]["server"]
    output["modules"]["kitsu"] = kitsu_settings


def _convert_timers_manager_system_settings(
    ayon_settings, output, addon_versions, default_settings
):
    enabled = addon_versions.get("timers_manager") is not None
    manager_settings = default_settings["modules"]["timers_manager"]
    manager_settings["enabled"] = enabled
    if enabled:
        ayon_manager = ayon_settings["timers_manager"]
        manager_settings.update({
            key: ayon_manager[key]
            for key in {
                "auto_stop",
                "full_time",
                "message_time",
                "disregard_publishing"
            }
        })
    output["modules"]["timers_manager"] = manager_settings


def _convert_clockify_system_settings(
    ayon_settings, output, addon_versions, default_settings
):
    enabled = addon_versions.get("clockify") is not None
    clockify_settings = default_settings["modules"]["clockify"]
    clockify_settings["enabled"] = enabled
    if enabled:
        clockify_settings["workspace_name"] = (
            ayon_settings["clockify"]["workspace_name"]
        )
    output["modules"]["clockify"] = clockify_settings


def _convert_deadline_system_settings(
    ayon_settings, output, addon_versions, default_settings
):
    enabled = addon_versions.get("deadline") is not None
    deadline_settings = default_settings["modules"]["deadline"]
    deadline_settings["enabled"] = enabled
    if enabled:
        ayon_deadline = ayon_settings["deadline"]
        deadline_settings["deadline_urls"] = {
            item["name"]: item["value"]
            for item in ayon_deadline["deadline_urls"]
        }

    output["modules"]["deadline"] = deadline_settings


def _convert_royalrender_system_settings(
    ayon_settings, output, addon_versions, default_settings
):
    enabled = addon_versions.get("royalrender") is not None
    rr_settings = default_settings["modules"]["royalrender"]
    rr_settings["enabled"] = enabled
    if enabled:
        ayon_royalrender = ayon_settings["royalrender"]
        rr_settings["rr_paths"] = {
            item["name"]: item["value"]
            for item in ayon_royalrender["rr_paths"]
        }
    output["modules"]["royalrender"] = rr_settings


def _convert_modules_system(
    ayon_settings, output, addon_versions, default_settings
):
    # TODO add all modules
    # TODO add 'enabled' values
    for func in (
        _convert_kitsu_system_settings,
        _convert_timers_manager_system_settings,
        _convert_clockify_system_settings,
        _convert_deadline_system_settings,
        _convert_royalrender_system_settings,
    ):
        func(ayon_settings, output, addon_versions, default_settings)

    modules_settings = output["modules"]
    for module_name in (
        "sync_server",
        "log_viewer",
        "standalonepublish_tool",
        "project_manager",
        "job_queue",
        "avalon",
        "addon_paths",
    ):
        settings = default_settings["modules"][module_name]
        if "enabled" in settings:
            settings["enabled"] = False
        modules_settings[module_name] = settings

    for key, value in ayon_settings.items():
        if key not in output:
            output[key] = value

        # Make sure addons have access to settings in initialization
        # - ModulesManager passes only modules settings into initialization
        if key not in modules_settings:
            modules_settings[key] = value


def is_dev_mode_enabled():
    """Dev mode is enabled in AYON.

    Returns:
        bool: True if dev mode is enabled.
    """

    return os.getenv("AYON_USE_DEV") == "1"


def convert_system_settings(ayon_settings, default_settings, addon_versions):
    default_settings = copy.deepcopy(default_settings)
    output = {
        "modules": {}
    }
    if "applications" in ayon_settings:
        _convert_applications_system_settings(ayon_settings, output, False)

    if "core" in ayon_settings:
        _convert_general(ayon_settings, output, default_settings)

    for key, value in ayon_settings.items():
        if key not in output:
            output[key] = value

    for key, value in default_settings.items():
        if key not in output:
            output[key] = value

    _convert_modules_system(
        ayon_settings,
        output,
        addon_versions,
        default_settings
    )
    return output


# --------- Project settings ---------
def _convert_applications_project_settings(ayon_settings, output):
    if "applications" not in ayon_settings:
        return

    output["applications"] = {
        "only_available": ayon_settings["applications"]["only_available"]
    }


def _convert_blender_project_settings(ayon_settings, output):
    if "blender" not in ayon_settings:
        return
    ayon_blender = ayon_settings["blender"]
    _convert_host_imageio(ayon_blender)

    ayon_publish = ayon_blender["publish"]

    for plugin in ("ExtractThumbnail", "ExtractPlayblast"):
        plugin_settings = ayon_publish[plugin]
        plugin_settings["presets"] = json.loads(plugin_settings["presets"])

    output["blender"] = ayon_blender


def _convert_celaction_project_settings(ayon_settings, output):
    if "celaction" not in ayon_settings:
        return

    ayon_celaction = ayon_settings["celaction"]
    _convert_host_imageio(ayon_celaction)

    output["celaction"] = ayon_celaction


def _convert_flame_project_settings(ayon_settings, output):
    if "flame" not in ayon_settings:
        return

    ayon_flame = ayon_settings["flame"]

    ayon_publish_flame = ayon_flame["publish"]
    # Plugin 'ExtractSubsetResources' renamed to 'ExtractProductResources'
    if "ExtractSubsetResources" in ayon_publish_flame:
        ayon_product_resources = ayon_publish_flame["ExtractSubsetResources"]
    else:
        ayon_product_resources = (
            ayon_publish_flame.pop("ExtractProductResources"))
        ayon_publish_flame["ExtractSubsetResources"] = ayon_product_resources

    # 'ExtractSubsetResources' changed model of 'export_presets_mapping'
    # - some keys were moved under 'other_parameters'
    new_subset_resources = {}
    for item in ayon_product_resources.pop("export_presets_mapping"):
        name = item.pop("name")
        if "other_parameters" in item:
            other_parameters = item.pop("other_parameters")
            item.update(other_parameters)
        new_subset_resources[name] = item

    ayon_product_resources["export_presets_mapping"] = new_subset_resources

    # 'imageio' changed model
    # - missing subkey 'project' which is in root of 'imageio' model
    _convert_host_imageio(ayon_flame)
    ayon_imageio_flame = ayon_flame["imageio"]
    if "project" not in ayon_imageio_flame:
        profile_mapping = ayon_imageio_flame.pop("profilesMapping")
        ayon_flame["imageio"] = {
            "project": ayon_imageio_flame,
            "profilesMapping": profile_mapping
        }

    ayon_load_flame = ayon_flame["load"]
    for plugin_name in ("LoadClip", "LoadClipBatch"):
        plugin_settings = ayon_load_flame[plugin_name]
        plugin_settings["families"] = plugin_settings.pop("product_types")
        plugin_settings["clip_name_template"] = (
            plugin_settings["clip_name_template"]
            .replace("{folder[name]}", "{asset}")
            .replace("{product[name]}", "{subset}")
        )
        plugin_settings["layer_rename_template"] = (
            plugin_settings["layer_rename_template"]
            .replace("{folder[name]}", "{asset}")
            .replace("{product[name]}", "{subset}")
        )

    output["flame"] = ayon_flame


def _convert_fusion_project_settings(ayon_settings, output):
    if "fusion" not in ayon_settings:
        return

    ayon_fusion = ayon_settings["fusion"]
    _convert_host_imageio(ayon_fusion)

    ayon_imageio_fusion = ayon_fusion["imageio"]

    if "ocioSettings" in ayon_imageio_fusion:
        ayon_ocio_setting = ayon_imageio_fusion.pop("ocioSettings")
        paths = ayon_ocio_setting.pop("ocioPathModel")
        for key, value in tuple(paths.items()):
            new_value = []
            if value:
                new_value.append(value)
            paths[key] = new_value

        ayon_ocio_setting["configFilePath"] = paths
        ayon_imageio_fusion["ocio"] = ayon_ocio_setting
    elif "ocio" in ayon_imageio_fusion:
        paths = ayon_imageio_fusion["ocio"].pop("configFilePath")
        for key, value in tuple(paths.items()):
            new_value = []
            if value:
                new_value.append(value)
            paths[key] = new_value
        ayon_imageio_fusion["ocio"]["configFilePath"] = paths

    _convert_host_imageio(ayon_imageio_fusion)

    ayon_create_saver = ayon_fusion["create"]["CreateSaver"]
    ayon_create_saver["temp_rendering_path_template"] = (
        ayon_create_saver["temp_rendering_path_template"]
        .replace("{product[name]}", "{subset}")
        .replace("{product[type]}", "{family}")
        .replace("{folder[name]}", "{asset}")
        .replace("{task[name]}", "{task}")
    )

    output["fusion"] = ayon_fusion


def _convert_maya_project_settings(ayon_settings, output):
    if "maya" not in ayon_settings:
        return

    ayon_maya = ayon_settings["maya"]

    # Change key of render settings
    ayon_maya["RenderSettings"] = ayon_maya.pop("render_settings")

    # Convert extensions mapping
    ayon_maya["ext_mapping"] = {
        item["name"]: item["value"]
        for item in ayon_maya["ext_mapping"]
    }

    # Maya dirmap
    ayon_maya_dirmap = ayon_maya.pop("maya_dirmap")
    ayon_maya_dirmap_path = ayon_maya_dirmap["paths"]
    ayon_maya_dirmap_path["source-path"] = (
        ayon_maya_dirmap_path.pop("source_path")
    )
    ayon_maya_dirmap_path["destination-path"] = (
        ayon_maya_dirmap_path.pop("destination_path")
    )
    ayon_maya["maya-dirmap"] = ayon_maya_dirmap

    # Create plugins
    ayon_create = ayon_maya["create"]
    ayon_create_static_mesh = ayon_create["CreateUnrealStaticMesh"]
    if "static_mesh_prefixes" in ayon_create_static_mesh:
        ayon_create_static_mesh["static_mesh_prefix"] = (
            ayon_create_static_mesh.pop("static_mesh_prefixes")
        )

    # --- Publish (START) ---
    ayon_publish = ayon_maya["publish"]
    try:
        attributes = json.loads(
            ayon_publish["ValidateAttributes"]["attributes"]
        )
    except ValueError:
        attributes = {}
    ayon_publish["ValidateAttributes"]["attributes"] = attributes

    try:
        SUFFIX_NAMING_TABLE = json.loads(
            ayon_publish
            ["ValidateTransformNamingSuffix"]
            ["SUFFIX_NAMING_TABLE"]
        )
    except ValueError:
        SUFFIX_NAMING_TABLE = {}
    ayon_publish["ValidateTransformNamingSuffix"]["SUFFIX_NAMING_TABLE"] = (
        SUFFIX_NAMING_TABLE
    )

    validate_frame_range = ayon_publish["ValidateFrameRange"]
    if "exclude_product_types" in validate_frame_range:
        validate_frame_range["exclude_families"] = (
            validate_frame_range.pop("exclude_product_types"))

    # Extract playblast capture settings
    validate_rendern_settings = ayon_publish["ValidateRenderSettings"]
    for key in (
        "arnold_render_attributes",
        "vray_render_attributes",
        "redshift_render_attributes",
        "renderman_render_attributes",
    ):
        if key not in validate_rendern_settings:
            continue
        validate_rendern_settings[key] = [
            [item["type"], item["value"]]
            for item in validate_rendern_settings[key]
        ]

    plugin_path_attributes = ayon_publish["ValidatePluginPathAttributes"]
    plugin_path_attributes["attribute"] = {
        item["name"]: item["value"]
        for item in plugin_path_attributes["attribute"]
    }

    ayon_capture_preset = ayon_publish["ExtractPlayblast"]["capture_preset"]
    display_options = ayon_capture_preset["DisplayOptions"]
    for key in ("background", "backgroundBottom", "backgroundTop"):
        display_options[key] = _convert_color(display_options[key])

    for src_key, dst_key in (
        ("DisplayOptions", "Display Options"),
        ("ViewportOptions", "Viewport Options"),
        ("CameraOptions", "Camera Options"),
    ):
        ayon_capture_preset[dst_key] = ayon_capture_preset.pop(src_key)

    viewport_options = ayon_capture_preset["Viewport Options"]
    viewport_options["pluginObjects"] = {
        item["name"]: item["value"]
        for item in viewport_options["pluginObjects"]
    }

    ayon_playblast_settings = ayon_publish["ExtractPlayblast"]["profiles"]
    if ayon_playblast_settings:
        for setting in ayon_playblast_settings:
            capture_preset = setting["capture_preset"]
            display_options = capture_preset["DisplayOptions"]
            for key in ("background", "backgroundBottom", "backgroundTop"):
                display_options[key] = _convert_color(display_options[key])

            for src_key, dst_key in (
                ("DisplayOptions", "Display Options"),
                ("ViewportOptions", "Viewport Options"),
                ("CameraOptions", "Camera Options"),
            ):
                capture_preset[dst_key] = capture_preset.pop(src_key)

            viewport_options = capture_preset["Viewport Options"]
            viewport_options["pluginObjects"] = {
                item["name"]: item["value"]
                for item in viewport_options["pluginObjects"]
            }

    # Extract Camera Alembic bake attributes
    try:
        bake_attributes = json.loads(
            ayon_publish["ExtractCameraAlembic"]["bake_attributes"]
        )
    except ValueError:
        bake_attributes = []
    ayon_publish["ExtractCameraAlembic"]["bake_attributes"] = bake_attributes

    # --- Publish (END) ---
    for renderer_settings in ayon_maya["RenderSettings"].values():
        if (
            not isinstance(renderer_settings, dict)
            or "additional_options" not in renderer_settings
        ):
            continue
        renderer_settings["additional_options"] = [
            [item["attribute"], item["value"]]
            for item in renderer_settings["additional_options"]
        ]

    # Workfile build
    ayon_workfile_build = ayon_maya["workfile_build"]
    for item in ayon_workfile_build["profiles"]:
        for key in ("current_context", "linked_assets"):
            for subitem in item[key]:
                if "families" in subitem:
                    break
                subitem["families"] = subitem.pop("product_types")
                subitem["subset_name_filters"] = subitem.pop(
                    "product_name_filters")

    _convert_host_imageio(ayon_maya)

    ayon_maya_load = ayon_maya["load"]
    load_colors = ayon_maya_load["colors"]
    for key, color in tuple(load_colors.items()):
        load_colors[key] = _convert_color(color)

    reference_loader = ayon_maya_load["reference_loader"]
    reference_loader["namespace"] = (
        reference_loader["namespace"]
        .replace("{product[name]}", "{subset}")
    )

    if ayon_maya_load.get("import_loader"):
        import_loader = ayon_maya_load["import_loader"]
        import_loader["namespace"] = (
            import_loader["namespace"]
            .replace("{product[name]}", "{subset}")
        )

    output["maya"] = ayon_maya


def _convert_3dsmax_project_settings(ayon_settings, output):
    if "max" not in ayon_settings:
        return

    ayon_max = ayon_settings["max"]
    _convert_host_imageio(ayon_max)
    if "PointCloud" in ayon_max:
        point_cloud_attribute = ayon_max["PointCloud"]["attribute"]
        new_point_cloud_attribute = {
            item["name"]: item["value"]
            for item in point_cloud_attribute
        }
        ayon_max["PointCloud"]["attribute"] = new_point_cloud_attribute
    # --- Publish (START) ---
    ayon_publish = ayon_max["publish"]
    if "ValidateAttributes" in ayon_publish:
        try:
            attributes = json.loads(
                ayon_publish["ValidateAttributes"]["attributes"]
            )
        except ValueError:
            attributes = {}
        ayon_publish["ValidateAttributes"]["attributes"] = attributes

    if "ValidateLoadedPlugin" in ayon_publish:
        loaded_plugin = (
            ayon_publish["ValidateLoadedPlugin"]["family_plugins_mapping"]
        )
        for item in loaded_plugin:
            item["families"] = item.pop("product_types")

    output["max"] = ayon_max


def _convert_nuke_knobs(knobs):
    new_knobs = []
    for knob in knobs:
        knob_type = knob["type"]

        if knob_type == "boolean":
            knob_type = "bool"

        if knob_type != "bool":
            value = knob[knob_type]
        elif knob_type in knob:
            value = knob[knob_type]
        else:
            value = knob["boolean"]

        new_knob = {
            "type": knob_type,
            "name": knob["name"],
        }
        new_knobs.append(new_knob)

        if knob_type == "formatable":
            new_knob["template"] = value["template"]
            new_knob["to_type"] = value["to_type"]
            continue

        value_key = "value"
        if knob_type == "expression":
            value_key = "expression"

        elif knob_type == "color_gui":
            value = _convert_color(value)

        elif knob_type == "vector_2d":
            value = [value["x"], value["y"]]

        elif knob_type == "vector_3d":
            value = [value["x"], value["y"], value["z"]]

        elif knob_type == "box":
            value = [value["x"], value["y"], value["r"], value["t"]]

        new_knob[value_key] = value
    return new_knobs


def _convert_nuke_project_settings(ayon_settings, output):
    if "nuke" not in ayon_settings:
        return

    ayon_nuke = ayon_settings["nuke"]

    # --- Dirmap ---
    dirmap = ayon_nuke.pop("dirmap")
    for src_key, dst_key in (
        ("source_path", "source-path"),
        ("destination_path", "destination-path"),
    ):
        dirmap["paths"][dst_key] = dirmap["paths"].pop(src_key)
    ayon_nuke["nuke-dirmap"] = dirmap

    # --- Load ---
    ayon_load = ayon_nuke["load"]
    ayon_load["LoadClip"]["_representations"] = (
        ayon_load["LoadClip"].pop("representations_include")
    )
    ayon_load["LoadImage"]["_representations"] = (
        ayon_load["LoadImage"].pop("representations_include")
    )

    # --- Create ---
    ayon_create = ayon_nuke["create"]
    for creator_name in (
        "CreateWritePrerender",
        "CreateWriteImage",
        "CreateWriteRender",
    ):
        create_plugin_settings = ayon_create[creator_name]
        create_plugin_settings["temp_rendering_path_template"] = (
            create_plugin_settings["temp_rendering_path_template"]
            .replace("{product[name]}", "{subset}")
            .replace("{product[type]}", "{family}")
            .replace("{task[name]}", "{task}")
            .replace("{folder[name]}", "{asset}")
        )
        new_prenodes = {}
        for prenode in create_plugin_settings["prenodes"]:
            name = prenode.pop("name")
            prenode["knobs"] = _convert_nuke_knobs(prenode["knobs"])
            new_prenodes[name] = prenode

        create_plugin_settings["prenodes"] = new_prenodes

    # --- Publish ---
    ayon_publish = ayon_nuke["publish"]
    slate_mapping = ayon_publish["ExtractSlateFrame"]["key_value_mapping"]
    for key in tuple(slate_mapping.keys()):
        value = slate_mapping[key]
        slate_mapping[key] = [value["enabled"], value["template"]]

    ayon_publish["ValidateKnobs"]["knobs"] = json.loads(
        ayon_publish["ValidateKnobs"]["knobs"]
    )

    new_review_data_outputs = {}
    outputs_settings = []
    # Check deprecated ExtractReviewDataMov
    # settings for backwards compatibility
    deprecrated_review_settings = ayon_publish["ExtractReviewDataMov"]
    current_review_settings = (
        ayon_publish.get("ExtractReviewIntermediates")
    )
    if deprecrated_review_settings["enabled"]:
        outputs_settings = deprecrated_review_settings["outputs"]
    elif current_review_settings is None:
        pass
    elif current_review_settings["enabled"]:
        outputs_settings = current_review_settings["outputs"]

    for item in outputs_settings:
        item_filter = item["filter"]
        if "product_names" in item_filter:
            item_filter["subsets"] = item_filter.pop("product_names")
            item_filter["families"] = item_filter.pop("product_types")

        reformat_nodes_config = item.get("reformat_nodes_config") or {}
        reposition_nodes = reformat_nodes_config.get(
            "reposition_nodes") or []

        for reposition_node in reposition_nodes:
            if "knobs" not in reposition_node:
                continue
            reposition_node["knobs"] = _convert_nuke_knobs(
                reposition_node["knobs"]
            )

        name = item.pop("name")
        new_review_data_outputs[name] = item

    if deprecrated_review_settings["enabled"]:
        deprecrated_review_settings["outputs"] = new_review_data_outputs
    elif current_review_settings["enabled"]:
        current_review_settings["outputs"] = new_review_data_outputs

    collect_instance_data = ayon_publish["CollectInstanceData"]
    if "sync_workfile_version_on_product_types" in collect_instance_data:
        collect_instance_data["sync_workfile_version_on_families"] = (
            collect_instance_data.pop(
                "sync_workfile_version_on_product_types"))

    # --- ImageIO ---
    # NOTE 'monitorOutLut' is maybe not yet in v3 (ut should be)
    _convert_host_imageio(ayon_nuke)
    ayon_imageio = ayon_nuke["imageio"]

    # workfile
    imageio_workfile = ayon_imageio["workfile"]
    workfile_keys_mapping = (
        ("color_management", "colorManagement"),
        ("native_ocio_config", "OCIO_config"),
        ("working_space", "workingSpaceLUT"),
        ("thumbnail_space", "monitorLut"),
    )
    for src, dst in workfile_keys_mapping:
        if (
            src in imageio_workfile
            and dst not in imageio_workfile
        ):
            imageio_workfile[dst] = imageio_workfile.pop(src)

    # regex inputs
    if "regex_inputs" in ayon_imageio:
        ayon_imageio["regexInputs"] = ayon_imageio.pop("regex_inputs")

    # nodes
    ayon_imageio_nodes = ayon_imageio["nodes"]
    if "required_nodes" in ayon_imageio_nodes:
        ayon_imageio_nodes["requiredNodes"] = (
            ayon_imageio_nodes.pop("required_nodes"))
    if "override_nodes" in ayon_imageio_nodes:
        ayon_imageio_nodes["overrideNodes"] = (
            ayon_imageio_nodes.pop("override_nodes"))

    for item in ayon_imageio_nodes["requiredNodes"]:
        if "nuke_node_class" in item:
            item["nukeNodeClass"] = item.pop("nuke_node_class")
        item["knobs"] = _convert_nuke_knobs(item["knobs"])

    for item in ayon_imageio_nodes["overrideNodes"]:
        if "nuke_node_class" in item:
            item["nukeNodeClass"] = item.pop("nuke_node_class")
        item["knobs"] = _convert_nuke_knobs(item["knobs"])

    output["nuke"] = ayon_nuke


def _convert_hiero_project_settings(ayon_settings, output):
    if "hiero" not in ayon_settings:
        return

    ayon_hiero = ayon_settings["hiero"]
    _convert_host_imageio(ayon_hiero)

    new_gui_filters = {}
    for item in ayon_hiero.pop("filters", []):
        subvalue = {}
        key = item["name"]
        for subitem in item["value"]:
            subvalue[subitem["name"]] = subitem["value"]
        new_gui_filters[key] = subvalue
    ayon_hiero["filters"] = new_gui_filters

    ayon_load_clip = ayon_hiero["load"]["LoadClip"]
    if "product_types" in ayon_load_clip:
        ayon_load_clip["families"] = ayon_load_clip.pop("product_types")

    ayon_load_clip = ayon_hiero["load"]["LoadClip"]
    ayon_load_clip["clip_name_template"] = (
        ayon_load_clip["clip_name_template"]
        .replace("{folder[name]}", "{asset}")
        .replace("{product[name]}", "{subset}")
    )

    output["hiero"] = ayon_hiero


def _convert_photoshop_project_settings(ayon_settings, output):
    if "photoshop" not in ayon_settings:
        return

    ayon_photoshop = ayon_settings["photoshop"]
    _convert_host_imageio(ayon_photoshop)

    ayon_publish_photoshop = ayon_photoshop["publish"]

    ayon_colorcoded = ayon_publish_photoshop["CollectColorCodedInstances"]
    if "flatten_product_type_template" in ayon_colorcoded:
        ayon_colorcoded["flatten_subset_template"] = (
            ayon_colorcoded.pop("flatten_product_type_template"))

    collect_review = ayon_publish_photoshop["CollectReview"]
    if "active" in collect_review:
        collect_review["publish"] = collect_review.pop("active")

    output["photoshop"] = ayon_photoshop


def _convert_substancepainter_project_settings(ayon_settings, output):
    if "substancepainter" not in ayon_settings:
        return

    ayon_substance_painter = ayon_settings["substancepainter"]
    _convert_host_imageio(ayon_substance_painter)
    if "shelves" in ayon_substance_painter:
        shelves_items = ayon_substance_painter["shelves"]
        new_shelves_items = {
            item["name"]: item["value"]
            for item in shelves_items
        }
        ayon_substance_painter["shelves"] = new_shelves_items

    output["substancepainter"] = ayon_substance_painter


def _convert_tvpaint_project_settings(ayon_settings, output):
    if "tvpaint" not in ayon_settings:
        return
    ayon_tvpaint = ayon_settings["tvpaint"]

    _convert_host_imageio(ayon_tvpaint)

    ayon_publish_settings = ayon_tvpaint["publish"]
    for plugin_name in (
        "ValidateProjectSettings",
        "ValidateMarks",
        "ValidateStartFrame",
        "ValidateAssetName",
    ):
        ayon_value = ayon_publish_settings[plugin_name]
        for src_key, dst_key in (
            ("action_enabled", "optional"),
            ("action_enable", "active"),
        ):
            if src_key in ayon_value:
                ayon_value[dst_key] = ayon_value.pop(src_key)

    extract_sequence_setting = ayon_publish_settings["ExtractSequence"]
    extract_sequence_setting["review_bg"] = _convert_color(
        extract_sequence_setting["review_bg"]
    )

    output["tvpaint"] = ayon_tvpaint


def _convert_traypublisher_project_settings(ayon_settings, output):
    if "traypublisher" not in ayon_settings:
        return

    ayon_traypublisher = ayon_settings["traypublisher"]

    _convert_host_imageio(ayon_traypublisher)

    ayon_editorial_simple = (
        ayon_traypublisher["editorial_creators"]["editorial_simple"]
    )
    # Subset -> Product type conversion
    if "product_type_presets" in ayon_editorial_simple:
        family_presets = ayon_editorial_simple.pop("product_type_presets")
        for item in family_presets:
            item["family"] = item.pop("product_type")
        ayon_editorial_simple["family_presets"] = family_presets

    if "shot_metadata_creator" in ayon_editorial_simple:
        shot_metadata_creator = ayon_editorial_simple.pop(
            "shot_metadata_creator"
        )
        if isinstance(shot_metadata_creator["clip_name_tokenizer"], dict):
            shot_metadata_creator["clip_name_tokenizer"] = [
                {"name": "_sequence_", "regex": "(sc\\d{3})"},
                {"name": "_shot_", "regex": "(sh\\d{3})"},
            ]
        ayon_editorial_simple.update(shot_metadata_creator)

    ayon_editorial_simple["clip_name_tokenizer"] = {
        item["name"]: item["regex"]
        for item in ayon_editorial_simple["clip_name_tokenizer"]
    }

    if "shot_subset_creator" in ayon_editorial_simple:
        ayon_editorial_simple.update(
            ayon_editorial_simple.pop("shot_subset_creator"))
    for item in ayon_editorial_simple["shot_hierarchy"]["parents"]:
        item["type"] = item.pop("parent_type")

    # Simple creators
    ayon_simple_creators = ayon_traypublisher["simple_creators"]
    for item in ayon_simple_creators:
        if "product_type" not in item:
            break
        item["family"] = item.pop("product_type")

    shot_add_tasks = ayon_editorial_simple["shot_add_tasks"]

    # TODO: backward compatibility and remove in future
    if isinstance(shot_add_tasks, dict):
        shot_add_tasks = []

    # aggregate shot_add_tasks items
    new_shot_add_tasks = {
        item["name"]: {"type": item["task_type"]}
        for item in shot_add_tasks
    }
    ayon_editorial_simple["shot_add_tasks"] = new_shot_add_tasks

    output["traypublisher"] = ayon_traypublisher


def _convert_webpublisher_project_settings(ayon_settings, output):
    if "webpublisher" not in ayon_settings:
        return

    ayon_webpublisher = ayon_settings["webpublisher"]
    _convert_host_imageio(ayon_webpublisher)

    ayon_publish = ayon_webpublisher["publish"]

    ayon_collect_files = ayon_publish["CollectPublishedFiles"]
    ayon_collect_files["task_type_to_family"] = {
        item["name"]: item["value"]
        for item in ayon_collect_files["task_type_to_family"]
    }

    output["webpublisher"] = ayon_webpublisher


def _convert_deadline_project_settings(ayon_settings, output):
    if "deadline" not in ayon_settings:
        return

    ayon_deadline = ayon_settings["deadline"]

    for key in ("deadline_urls",):
        ayon_deadline.pop(key)

    ayon_deadline_publish = ayon_deadline["publish"]
    limit_groups = {
        item["name"]: item["value"]
        for item in ayon_deadline_publish["NukeSubmitDeadline"]["limit_groups"]
    }
    ayon_deadline_publish["NukeSubmitDeadline"]["limit_groups"] = limit_groups

    maya_submit = ayon_deadline_publish["MayaSubmitDeadline"]
    for json_key in ("jobInfo", "pluginInfo"):
        src_text = maya_submit.pop(json_key)
        try:
            value = json.loads(src_text)
        except ValueError:
            value = {}
        maya_submit[json_key] = value

    nuke_submit = ayon_deadline_publish["NukeSubmitDeadline"]
    nuke_submit["env_search_replace_values"] = {
        item["name"]: item["value"]
        for item in nuke_submit.pop("env_search_replace_values")
    }
    nuke_submit["limit_groups"] = {
        item["name"]: item["value"] for item in nuke_submit.pop("limit_groups")
    }

    process_subsetted_job = ayon_deadline_publish["ProcessSubmittedJobOnFarm"]
    process_subsetted_job["aov_filter"] = {
        item["name"]: item["value"]
        for item in process_subsetted_job.pop("aov_filter")
    }

    output["deadline"] = ayon_deadline


def _convert_royalrender_project_settings(ayon_settings, output):
    if "royalrender" not in ayon_settings:
        return
    ayon_royalrender = ayon_settings["royalrender"]
    rr_paths = ayon_royalrender.get("selected_rr_paths", [])

    output["royalrender"] = {
        "publish": ayon_royalrender["publish"],
        "rr_paths": rr_paths,
    }


def _convert_kitsu_project_settings(ayon_settings, output):
    if "kitsu" not in ayon_settings:
        return

    ayon_kitsu_settings = ayon_settings["kitsu"]
    ayon_kitsu_settings.pop("server")

    integrate_note = ayon_kitsu_settings["publish"]["IntegrateKitsuNote"]
    status_change_conditions = integrate_note["status_change_conditions"]
    if "product_type_requirements" in status_change_conditions:
        status_change_conditions["family_requirements"] = (
            status_change_conditions.pop("product_type_requirements"))

    output["kitsu"] = ayon_kitsu_settings


def _convert_shotgrid_project_settings(ayon_settings, output):
    if "shotgrid" not in ayon_settings:
        return

    ayon_shotgrid = ayon_settings["shotgrid"]
    # This means that a different variant of addon is used
    if "leecher_backend_url" not in ayon_shotgrid:
        return

    for key in {
        "leecher_backend_url",
        "filter_projects_by_login",
        "shotgrid_settings",
        "leecher_manager_url",
    }:
        ayon_shotgrid.pop(key)

    asset_field = ayon_shotgrid["fields"]["asset"]
    asset_field["type"] = asset_field.pop("asset_type")

    task_field = ayon_shotgrid["fields"]["task"]
    if "task" in task_field:
        task_field["step"] = task_field.pop("task")

    output["shotgrid"] = ayon_settings["shotgrid"]


def _convert_slack_project_settings(ayon_settings, output):
    if "slack" not in ayon_settings:
        return

    ayon_slack = ayon_settings["slack"]
    ayon_slack.pop("enabled", None)
    for profile in ayon_slack["publish"]["CollectSlackFamilies"]["profiles"]:
        profile["tasks"] = profile.pop("task_names")
        profile["subsets"] = profile.pop("subset_names")

    output["slack"] = ayon_slack


def _convert_global_project_settings(ayon_settings, output, default_settings):
    if "core" not in ayon_settings:
        return

    ayon_core = ayon_settings["core"]

    _convert_host_imageio(ayon_core)

    for key in (
        "environments",
        "studio_name",
        "studio_code",
    ):
        ayon_core.pop(key, None)

    # Publish conversion
    ayon_publish = ayon_core["publish"]

    ayon_collect_audio = ayon_publish["CollectAudio"]
    if "audio_product_name" in ayon_collect_audio:
        ayon_collect_audio["audio_subset_name"] = (
            ayon_collect_audio.pop("audio_product_name"))

    for profile in ayon_publish["ExtractReview"]["profiles"]:
        if "product_types" in profile:
            profile["families"] = profile.pop("product_types")
        new_outputs = {}
        for output_def in profile.pop("outputs"):
            name = output_def.pop("name")
            new_outputs[name] = output_def

            output_def_filter = output_def["filter"]
            if "product_names" in output_def_filter:
                output_def_filter["subsets"] = (
                    output_def_filter.pop("product_names"))

            for color_key in ("overscan_color", "bg_color"):
                output_def[color_key] = _convert_color(output_def[color_key])

            letter_box = output_def["letter_box"]
            for color_key in ("fill_color", "line_color"):
                letter_box[color_key] = _convert_color(letter_box[color_key])

            if "output_width" in output_def:
                output_def["width"] = output_def.pop("output_width")

            if "output_height" in output_def:
                output_def["height"] = output_def.pop("output_height")

        profile["outputs"] = new_outputs

    # ExtractThumbnail plugin
    ayon_extract_thumbnail = ayon_publish["ExtractThumbnail"]
    # fix display and view at oiio defaults
    ayon_default_oiio = copy.deepcopy(
        ayon_extract_thumbnail["oiiotool_defaults"])
    display_and_view = ayon_default_oiio.pop("display_and_view")
    ayon_default_oiio["display"] = display_and_view["display"]
    ayon_default_oiio["view"] = display_and_view["view"]
    ayon_extract_thumbnail["oiiotool_defaults"] = ayon_default_oiio
    # fix target size
    ayon_default_resize = copy.deepcopy(ayon_extract_thumbnail["target_size"])
    resize = ayon_default_resize.pop("resize")
    ayon_default_resize["width"] = resize["width"]
    ayon_default_resize["height"] = resize["height"]
    ayon_extract_thumbnail["target_size"] = ayon_default_resize
    # fix background color
    ayon_extract_thumbnail["background_color"] = _convert_color(
        ayon_extract_thumbnail["background_color"]
    )

    # ExtractOIIOTranscode plugin
    extract_oiio_transcode = ayon_publish["ExtractOIIOTranscode"]
    extract_oiio_transcode_profiles = extract_oiio_transcode["profiles"]
    for profile in extract_oiio_transcode_profiles:
        new_outputs = {}
        name_counter = {}
        if "product_names" in profile:
            profile["subsets"] = profile.pop("product_names")
        for profile_output in profile["outputs"]:
            if "name" in profile_output:
                name = profile_output.pop("name")
            else:
                # Backwards compatibility for setting without 'name' in model
                name = profile_output["extension"]
                if name in new_outputs:
                    name_counter[name] += 1
                    name = "{}_{}".format(name, name_counter[name])
                else:
                    name_counter[name] = 0

            new_outputs[name] = profile_output
        profile["outputs"] = new_outputs

    # Extract Burnin plugin
    extract_burnin = ayon_publish["ExtractBurnin"]
    extract_burnin_options = extract_burnin["options"]
    for color_key in ("font_color", "bg_color"):
        extract_burnin_options[color_key] = _convert_color(
            extract_burnin_options[color_key]
        )

    for profile in extract_burnin["profiles"]:
        extract_burnin_defs = profile["burnins"]
        if "product_names" in profile:
            profile["subsets"] = profile.pop("product_names")
            profile["families"] = profile.pop("product_types")

        for burnin_def in extract_burnin_defs:
            for key in (
                "TOP_LEFT",
                "TOP_CENTERED",
                "TOP_RIGHT",
                "BOTTOM_LEFT",
                "BOTTOM_CENTERED",
                "BOTTOM_RIGHT",
            ):
                burnin_def[key] = (
                    burnin_def[key]
                    .replace("{product[name]}", "{subset}")
                    .replace("{Product[name]}", "{Subset}")
                    .replace("{PRODUCT[NAME]}", "{SUBSET}")
                    .replace("{product[type]}", "{family}")
                    .replace("{Product[type]}", "{Family}")
                    .replace("{PRODUCT[TYPE]}", "{FAMILY}")
                    .replace("{folder[name]}", "{asset}")
                    .replace("{Folder[name]}", "{Asset}")
                    .replace("{FOLDER[NAME]}", "{ASSET}")
                )
        profile["burnins"] = {
            extract_burnin_def.pop("name"): extract_burnin_def
            for extract_burnin_def in extract_burnin_defs
        }

    if "IntegrateProductGroup" in ayon_publish:
        subset_group = ayon_publish.pop("IntegrateProductGroup")
        subset_group_profiles = subset_group.pop("product_grouping_profiles")
        for profile in subset_group_profiles:
            profile["families"] = profile.pop("product_types")
        subset_group["subset_grouping_profiles"] = subset_group_profiles
        ayon_publish["IntegrateSubsetGroup"] = subset_group

    # Cleanup plugin
    ayon_cleanup = ayon_publish["CleanUp"]
    if "patterns" in ayon_cleanup:
        ayon_cleanup["paterns"] = ayon_cleanup.pop("patterns")

    # Project root settings - json string to dict
    ayon_core["project_environments"] = json.loads(
        ayon_core["project_environments"]
    )
    ayon_core["project_folder_structure"] = json.dumps(json.loads(
        ayon_core["project_folder_structure"]
    ))

    # Tools settings
    ayon_tools = ayon_core["tools"]
    ayon_create_tool = ayon_tools["creator"]
    if "product_name_profiles" in ayon_create_tool:
        product_name_profiles = ayon_create_tool.pop("product_name_profiles")
        for profile in product_name_profiles:
            profile["families"] = profile.pop("product_types")
        ayon_create_tool["subset_name_profiles"] = product_name_profiles

    for profile in ayon_create_tool["subset_name_profiles"]:
        template = profile["template"]
        profile["template"] = (
            template
            .replace("{task[name]}", "{task}")
            .replace("{Task[name]}", "{Task}")
            .replace("{TASK[NAME]}", "{TASK}")
            .replace("{product[type]}", "{family}")
            .replace("{Product[type]}", "{Family}")
            .replace("{PRODUCT[TYPE]}", "{FAMILY}")
            .replace("{folder[name]}", "{asset}")
            .replace("{Folder[name]}", "{Asset}")
            .replace("{FOLDER[NAME]}", "{ASSET}")
        )

    product_smart_select_key = "families_smart_select"
    if "product_types_smart_select" in ayon_create_tool:
        product_smart_select_key = "product_types_smart_select"

    new_smart_select_families = {
        item["name"]: item["task_names"]
        for item in ayon_create_tool.pop(product_smart_select_key)
    }
    ayon_create_tool["families_smart_select"] = new_smart_select_families

    ayon_loader_tool = ayon_tools["loader"]
    if "product_type_filter_profiles" in ayon_loader_tool:
        product_type_filter_profiles = (
            ayon_loader_tool.pop("product_type_filter_profiles"))
        for profile in product_type_filter_profiles:
            profile["filter_families"] = profile.pop("filter_product_types")

        ayon_loader_tool["family_filter_profiles"] = (
            product_type_filter_profiles)

    ayon_publish_tool = ayon_tools["publish"]
    for profile in ayon_publish_tool["hero_template_name_profiles"]:
        if "product_types" in profile:
            profile["families"] = profile.pop("product_types")

    for profile in ayon_publish_tool["template_name_profiles"]:
        if "product_types" in profile:
            profile["families"] = profile.pop("product_types")

    ayon_core["sync_server"] = (
        default_settings["global"]["sync_server"]
    )
    output["global"] = ayon_core


def convert_project_settings(ayon_settings, default_settings):
    # Missing settings
    # - standalonepublisher
    default_settings = copy.deepcopy(default_settings)
    output = {}
    exact_match = {
        "aftereffects",
        "harmony",
        "houdini",
        "resolve",
        "unreal",
    }
    for key in exact_match:
        if key in ayon_settings:
            output[key] = ayon_settings[key]
            _convert_host_imageio(output[key])

    _convert_applications_project_settings(ayon_settings, output)
    _convert_blender_project_settings(ayon_settings, output)
    _convert_celaction_project_settings(ayon_settings, output)
    _convert_flame_project_settings(ayon_settings, output)
    _convert_fusion_project_settings(ayon_settings, output)
    _convert_maya_project_settings(ayon_settings, output)
    _convert_3dsmax_project_settings(ayon_settings, output)
    _convert_nuke_project_settings(ayon_settings, output)
    _convert_hiero_project_settings(ayon_settings, output)
    _convert_photoshop_project_settings(ayon_settings, output)
    _convert_substancepainter_project_settings(ayon_settings, output)
    _convert_tvpaint_project_settings(ayon_settings, output)
    _convert_traypublisher_project_settings(ayon_settings, output)
    _convert_webpublisher_project_settings(ayon_settings, output)

    _convert_deadline_project_settings(ayon_settings, output)
    _convert_royalrender_project_settings(ayon_settings, output)
    _convert_kitsu_project_settings(ayon_settings, output)
    _convert_shotgrid_project_settings(ayon_settings, output)
    _convert_slack_project_settings(ayon_settings, output)

    _convert_global_project_settings(ayon_settings, output, default_settings)

    for key, value in ayon_settings.items():
        if key not in output:
            output[key] = value

    for key, value in default_settings.items():
        if key not in output:
            output[key] = value

    return output


class CacheItem:
    lifetime = 10

    def __init__(self, value, outdate_time=None):
        self._value = value
        if outdate_time is None:
            outdate_time = time.time() + self.lifetime
        self._outdate_time = outdate_time

    @classmethod
    def create_outdated(cls):
        return cls({}, 0)

    def get_value(self):
        return copy.deepcopy(self._value)

    def update_value(self, value):
        self._value = value
        self._outdate_time = time.time() + self.lifetime

    @property
    def is_outdated(self):
        return time.time() > self._outdate_time


class _AyonSettingsCache:
    use_bundles = None
    variant = None
    addon_versions = CacheItem.create_outdated()
    studio_settings = CacheItem.create_outdated()
    cache_by_project_name = collections.defaultdict(
        CacheItem.create_outdated)

    @classmethod
    def _use_bundles(cls):
        if _AyonSettingsCache.use_bundles is None:
            con = get_ayon_server_api_connection()
            major, minor, _, _, _ = con.get_server_version_tuple()
            use_bundles = True
            if (major, minor) < (0, 3):
                use_bundles = False
            _AyonSettingsCache.use_bundles = use_bundles
        return _AyonSettingsCache.use_bundles

    @classmethod
    def _get_variant(cls):
        if _AyonSettingsCache.variant is None:
            from openpype.lib.openpype_version import is_staging_enabled

            variant = "production"
            if is_dev_mode_enabled():
                variant = cls._get_bundle_name()
            elif is_staging_enabled():
                variant = "staging"

            # Cache variant
            _AyonSettingsCache.variant = variant

            # Set the variant to global ayon api connection
            con = get_ayon_server_api_connection()
            con.set_default_settings_variant(variant)
        return _AyonSettingsCache.variant

    @classmethod
    def _get_bundle_name(cls):
        return os.environ["AYON_BUNDLE_NAME"]

    @classmethod
    def get_value_by_project(cls, project_name):
        cache_item = _AyonSettingsCache.cache_by_project_name[project_name]
        if cache_item.is_outdated:
            con = get_ayon_server_api_connection()
            if cls._use_bundles():
                value = con.get_addons_settings(
                    bundle_name=cls._get_bundle_name(),
                    project_name=project_name,
                    variant=cls._get_variant()
                )
            else:
                value = con.get_addons_settings(project_name)
            cache_item.update_value(value)
        return cache_item.get_value()

    @classmethod
    def _get_addon_versions_from_bundle(cls):
        con = get_ayon_server_api_connection()
        expected_bundle = cls._get_bundle_name()
        bundles = con.get_bundles()["bundles"]
        bundle = next(
            (
                bundle
                for bundle in bundles
                if bundle["name"] == expected_bundle
            ),
            None
        )
        if bundle is not None:
            return bundle["addons"]
        return {}

    @classmethod
    def get_addon_versions(cls):
        cache_item = _AyonSettingsCache.addon_versions
        if cache_item.is_outdated:
            if cls._use_bundles():
                addons = cls._get_addon_versions_from_bundle()
            else:
                con = get_ayon_server_api_connection()
                settings_data = con.get_addons_settings(
                    only_values=False,
                    variant=cls._get_variant()
                )
                addons = settings_data["versions"]
            cache_item.update_value(addons)

        return cache_item.get_value()


def get_ayon_project_settings(default_values, project_name):
    ayon_settings = _AyonSettingsCache.get_value_by_project(project_name)
    return convert_project_settings(ayon_settings, default_values)


def get_ayon_system_settings(default_values):
    addon_versions = _AyonSettingsCache.get_addon_versions()
    ayon_settings = _AyonSettingsCache.get_value_by_project(None)

    return convert_system_settings(
        ayon_settings, default_values, addon_versions
    )


def get_ayon_settings(project_name=None):
    """AYON studio settings.

    Raw AYON settings values.

    Args:
        project_name (Optional[str]): Project name.

    Returns:
        dict[str, Any]: AYON settings.
    """

    return _AyonSettingsCache.get_value_by_project(project_name)
