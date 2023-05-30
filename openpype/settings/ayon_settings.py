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

import json
import copy
import time

import six
import ayon_api


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
    if "adsk_3dsmax" in ayon_apps:
        ayon_apps["3dsmax"] = ayon_apps.pop("adsk_3dsmax")

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
        "environments": environments
    })
    output["general"] = general


def _convert_kitsu_system_settings(ayon_settings, output):
    output["modules"]["kitsu"] = {
        "server": ayon_settings["kitsu"]["server"]
    }


def _convert_ftrack_system_settings(ayon_settings, output, defaults):
    # Ftrack contains few keys that are needed for initialization in OpenPype
    #   mode and some are used on different places
    ftrack_settings = defaults["modules"]["ftrack"]
    ftrack_settings["ftrack_server"] = (
        ayon_settings["ftrack"]["ftrack_server"])
    output["modules"]["ftrack"] = ftrack_settings


def _convert_shotgrid_system_settings(ayon_settings, output):
    ayon_shotgrid = ayon_settings["shotgrid"]
    # Skip conversion if different ayon addon is used
    if "leecher_manager_url" not in ayon_shotgrid:
        output["shotgrid"] = ayon_shotgrid
        return

    shotgrid_settings = {}
    for key in (
        "leecher_manager_url",
        "leecher_backend_url",
        "filter_projects_by_login",
    ):
        shotgrid_settings[key] = ayon_shotgrid[key]

    new_items = {}
    for item in ayon_shotgrid["shotgrid_settings"]:
        name = item.pop("name")
        new_items[name] = item
    shotgrid_settings["shotgrid_settings"] = new_items

    output["modules"]["shotgrid"] = shotgrid_settings


def _convert_timers_manager_system_settings(ayon_settings, output):
    ayon_manager = ayon_settings["timers_manager"]
    manager_settings = {
        key: ayon_manager[key]
        for key in {
            "auto_stop", "full_time", "message_time", "disregard_publishing"
        }
    }
    output["modules"]["timers_manager"] = manager_settings


def _convert_clockify_system_settings(ayon_settings, output):
    output["modules"]["clockify"] = ayon_settings["clockify"]


def _convert_deadline_system_settings(ayon_settings, output):
    ayon_deadline = ayon_settings["deadline"]
    deadline_settings = {
        "deadline_urls": {
            item["name"]: item["value"]
            for item in ayon_deadline["deadline_urls"]
        }
    }
    output["modules"]["deadline"] = deadline_settings


def _convert_muster_system_settings(ayon_settings, output):
    ayon_muster = ayon_settings["muster"]
    templates_mapping = {
        item["name"]: item["value"]
        for item in ayon_muster["templates_mapping"]
    }
    output["modules"]["muster"] = {
        "templates_mapping": templates_mapping,
        "MUSTER_REST_URL": ayon_muster["MUSTER_REST_URL"]
    }


def _convert_royalrender_system_settings(ayon_settings, output):
    ayon_royalrender = ayon_settings["royalrender"]
    output["modules"]["royalrender"] = {
        "rr_paths": {
            item["name"]: item["value"]
            for item in ayon_royalrender["rr_paths"]
        }
    }


def _convert_modules_system(
    ayon_settings, output, addon_versions, default_settings
):
    # TODO add all modules
    # TODO add 'enabled' values
    for key, func in (
        ("kitsu", _convert_kitsu_system_settings),
        ("shotgrid", _convert_shotgrid_system_settings),
        ("timers_manager", _convert_timers_manager_system_settings),
        ("clockify", _convert_clockify_system_settings),
        ("deadline", _convert_deadline_system_settings),
        ("muster", _convert_muster_system_settings),
        ("royalrender", _convert_royalrender_system_settings),
    ):
        if key in ayon_settings:
            func(ayon_settings, output)

    if "ftrack" in ayon_settings:
        _convert_ftrack_system_settings(
            ayon_settings, output, default_settings)

    output_modules = output["modules"]
    # TODO remove when not needed
    for module_name, value in default_settings["modules"].items():
        if module_name not in output_modules:
            output_modules[module_name] = value

    for module_name, value in default_settings["modules"].items():
        if "enabled" not in value or module_name not in output_modules:
            continue

        output_modules[module_name]["enabled"] = module_name in addon_versions

    # Missing modules conversions
    # - "sync_server" -> renamed to sitesync
    # - "slack" -> only 'enabled'
    # - "job_queue" -> completelly missing in ayon


def convert_system_settings(ayon_settings, default_settings, addon_versions):
    default_settings = copy.deepcopy(default_settings)
    output = {
        "modules": {}
    }
    if "applications" in ayon_settings:
        _convert_applications_system_settings(ayon_settings, output, False)

    if "core" in ayon_settings:
        _convert_general(ayon_settings, output, default_settings)

    _convert_modules_system(
        ayon_settings,
        output,
        addon_versions,
        default_settings
    )
    for key, value in default_settings.items():
        if key not in output:
            output[key] = value
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
    # 'ExtractSubsetResources' changed model of 'export_presets_mapping'
    # - some keys were moved under 'other_parameters'
    ayon_subset_resources = ayon_publish_flame["ExtractSubsetResources"]
    new_subset_resources = {}
    for item in ayon_subset_resources.pop("export_presets_mapping"):
        name = item.pop("name")
        if "other_parameters" in item:
            other_parameters = item.pop("other_parameters")
            item.update(other_parameters)
        new_subset_resources[name] = item

    ayon_subset_resources["export_presets_mapping"] = new_subset_resources

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
    else:
        paths = ayon_imageio_fusion["ocio"].pop("configFilePath")
        for key, value in tuple(paths.items()):
            new_value = []
            if value:
                new_value.append(value)
            paths[key] = new_value
        ayon_imageio_fusion["ocio"]["configFilePath"] = paths

    _convert_host_imageio(ayon_imageio_fusion)

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

    # Publish UI filters
    new_filters = {}
    for item in ayon_maya["filters"]:
        new_filters[item["name"]] = {
            subitem["name"]: subitem["value"]
            for subitem in item["value"]
        }
    ayon_maya["filters"] = new_filters

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

    _convert_host_imageio(ayon_maya)

    load_colors = ayon_maya["load"]["colors"]
    for key, color in tuple(load_colors.items()):
        load_colors[key] = _convert_color(color)

    output["maya"] = ayon_maya


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

    # --- Filters ---
    new_gui_filters = {}
    for item in ayon_nuke.pop("filters"):
        subvalue = {}
        key = item["name"]
        for subitem in item["value"]:
            subvalue[subitem["name"]] = subitem["value"]
        new_gui_filters[key] = subvalue
    ayon_nuke["filters"] = new_gui_filters

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
        new_prenodes = {}
        for prenode in ayon_create[creator_name]["prenodes"]:
            name = prenode.pop("name")
            prenode["knobs"] = _convert_nuke_knobs(prenode["knobs"])
            new_prenodes[name] = prenode

        ayon_create[creator_name]["prenodes"] = new_prenodes

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
    for item in ayon_publish["ExtractReviewDataMov"]["outputs"]:
        item["reformat_node_config"] = _convert_nuke_knobs(
            item["reformat_node_config"])

        for node in item["reformat_nodes_config"]["reposition_nodes"]:
            node["knobs"] = _convert_nuke_knobs(node["knobs"])

        name = item.pop("name")
        new_review_data_outputs[name] = item

    ayon_publish["ExtractReviewDataMov"]["outputs"] = new_review_data_outputs

    # TODO 'ExtractThumbnail' does not have ideal schema in v3
    new_thumbnail_nodes = {}
    for item in ayon_publish["ExtractThumbnail"]["nodes"]:
        name = item["nodeclass"]
        value = []
        for knob in _convert_nuke_knobs(item["knobs"]):
            knob_name = knob["name"]
            # This may crash
            if knob["type"] == "expression":
                knob_value = knob["expression"]
            else:
                knob_value = knob["value"]
            value.append([knob_name, knob_value])
        new_thumbnail_nodes[name] = value

    ayon_publish["ExtractThumbnail"]["nodes"] = new_thumbnail_nodes

    # --- ImageIO ---
    # NOTE 'monitorOutLut' is maybe not yet in v3 (ut should be)
    _convert_host_imageio(ayon_nuke)
    ayon_imageio = ayon_nuke["imageio"]
    for item in ayon_imageio["nodes"]["requiredNodes"]:
        item["knobs"] = _convert_nuke_knobs(item["knobs"])
    for item in ayon_imageio["nodes"]["overrideNodes"]:
        item["knobs"] = _convert_nuke_knobs(item["knobs"])

    output["nuke"] = ayon_nuke


def _convert_hiero_project_settings(ayon_settings, output):
    if "hiero" not in ayon_settings:
        return

    ayon_hiero = ayon_settings["hiero"]
    _convert_host_imageio(ayon_hiero)

    new_gui_filters = {}
    for item in ayon_hiero.pop("filters"):
        subvalue = {}
        key = item["name"]
        for subitem in item["value"]:
            subvalue[subitem["name"]] = subitem["value"]
        new_gui_filters[key] = subvalue
    ayon_hiero["filters"] = new_gui_filters

    output["hiero"] = ayon_hiero


def _convert_photoshop_project_settings(ayon_settings, output):
    if "photoshop" not in ayon_settings:
        return

    ayon_photoshop = ayon_settings["photoshop"]
    _convert_host_imageio(ayon_photoshop)

    collect_review = ayon_photoshop["publish"]["CollectReview"]
    if "active" in collect_review:
        collect_review["publish"] = collect_review.pop("active")

    output["photoshop"] = ayon_photoshop


def _convert_tvpaint_project_settings(ayon_settings, output):
    if "tvpaint" not in ayon_settings:
        return
    ayon_tvpaint = ayon_settings["tvpaint"]

    _convert_host_imageio(ayon_tvpaint)

    filters = {}
    for item in ayon_tvpaint["filters"]:
        value = item["value"]
        try:
            value = json.loads(value)

        except ValueError:
            value = {}
        filters[item["name"]] = value
    ayon_tvpaint["filters"] = filters

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

    shot_add_tasks = ayon_editorial_simple["shot_add_tasks"]
    if isinstance(shot_add_tasks, dict):
        shot_add_tasks = []
    new_shot_add_tasks = {
        item["name"]: item["task_type"]
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
    output["royalrender"] = {
        "publish": ayon_royalrender["publish"]
    }


def _convert_kitsu_project_settings(ayon_settings, output):
    if "kitsu" not in ayon_settings:
        return

    ayon_kitsu_settings = ayon_settings["kitsu"]
    ayon_kitsu_settings.pop("server")
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
        ayon_core.pop(key)

    # Publish conversion
    ayon_publish = ayon_core["publish"]
    for profile in ayon_publish["ExtractReview"]["profiles"]:
        new_outputs = {}
        for output_def in profile.pop("outputs"):
            name = output_def.pop("name")
            new_outputs[name] = output_def

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

    extract_burnin = ayon_publish["ExtractBurnin"]
    extract_burnin_options = extract_burnin["options"]
    for color_key in ("font_color", "bg_color"):
        extract_burnin_options[color_key] = _convert_color(
            extract_burnin_options[color_key]
        )

    for profile in extract_burnin["profiles"]:
        extract_burnin_defs = profile["burnins"]
        profile["burnins"] = {
            extract_burnin_def.pop("name"): extract_burnin_def
            for extract_burnin_def in extract_burnin_defs
        }

    ayon_cleanup = ayon_publish["CleanUp"]
    if "patterns" in ayon_cleanup:
        ayon_cleanup["paterns"] = ayon_cleanup.pop("patterns")

    # Project root settings
    ayon_core["project_environments"] = json.loads(
        ayon_core["project_environments"]
    )
    ayon_core["project_folder_structure"] = json.dumps(json.loads(
        ayon_core["project_folder_structure"]
    ))

    # Tools settings
    ayon_tools = ayon_core["tools"]
    ayon_create_tool = ayon_tools["creator"]
    new_smart_select_families = {
        item["name"]: item["task_names"]
        for item in ayon_create_tool["families_smart_select"]
    }
    ayon_create_tool["families_smart_select"] = new_smart_select_families

    ayon_loader_tool = ayon_tools["loader"]
    for profile in ayon_loader_tool["family_filter_profiles"]:
        if "template_publish_families" in profile:
            profile["filter_families"] = (
                profile.pop("template_publish_families")
            )

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
    _convert_nuke_project_settings(ayon_settings, output)
    _convert_hiero_project_settings(ayon_settings, output)
    _convert_photoshop_project_settings(ayon_settings, output)
    _convert_tvpaint_project_settings(ayon_settings, output)
    _convert_traypublisher_project_settings(ayon_settings, output)
    _convert_webpublisher_project_settings(ayon_settings, output)

    _convert_deadline_project_settings(ayon_settings, output)
    _convert_royalrender_project_settings(ayon_settings, output)
    _convert_kitsu_project_settings(ayon_settings, output)
    _convert_shotgrid_project_settings(ayon_settings, output)
    _convert_slack_project_settings(ayon_settings, output)

    _convert_global_project_settings(ayon_settings, output, default_settings)

    for key, value in default_settings.items():
        if key not in output:
            output[key] = value

    return output


class CacheItem:
    lifetime = 10

    def __init__(self, value):
        self._value = value
        self._outdate_time = time.time() + self.lifetime

    def get_value(self):
        return copy.deepcopy(self._value)

    def update_value(self, value):
        self._value = value
        self._outdate_time = time.time() + self.lifetime

    @property
    def is_outdated(self):
        return time.time() > self._outdate_time


class AyonSettingsCache:
    _cache_by_project_name = {}
    _production_settings = None

    @classmethod
    def get_production_settings(cls):
        if (
            cls._production_settings is None
            or cls._production_settings.is_outdated
        ):
            from openpype.lib.openpype_version import is_staging_enabled

            variant = "staging" if is_staging_enabled() else "production"
            value = ayon_api.get_addons_settings(
                only_values=False, variant=variant)
            if cls._production_settings is None:
                cls._production_settings = CacheItem(value)
            else:
                cls._production_settings.update_value(value)
        return cls._production_settings.get_value()

    @classmethod
    def get_value_by_project(cls, project_name):
        production_settings = cls.get_production_settings()
        addon_versions = production_settings["versions"]
        if project_name is None:
            return production_settings["settings"], addon_versions

        cache_item = cls._cache_by_project_name.get(project_name)
        if cache_item is None or cache_item.is_outdated:
            value = ayon_api.get_addons_settings(project_name)
            if cache_item is None:
                cache_item = CacheItem(value)
                cls._cache_by_project_name[project_name] = cache_item
            else:
                cache_item.update_value(value)

        return cache_item.get_value(), addon_versions


def get_ayon_project_settings(default_values, project_name):
    ayon_settings, addon_versions = (
        AyonSettingsCache.get_value_by_project(project_name)
    )
    return convert_project_settings(ayon_settings, default_values)


def get_ayon_system_settings(default_values):
    ayon_settings, addon_versions = (
        AyonSettingsCache.get_value_by_project(None)
    )
    return convert_system_settings(
        ayon_settings, default_values, addon_versions
    )
