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
            variant_dynamic_labels[variant_name] = variant.pop("label")
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


def _convert_applications(ayon_settings, output, clear_metadata):
    # Addon settings
    addon_settings = ayon_settings["applications"]

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


def _convert_general(ayon_settings, output):
    # TODO get studio name/code
    core_settings = ayon_settings["core"]
    environments = core_settings["environments"]
    if isinstance(environments, six.string_types):
        environments = json.loads(environments)

    output["general"].update({
        "log_to_server": False,
        "studio_name": core_settings["studio_name"],
        "studio_code": core_settings["studio_code"],
        "environments": environments
    })


def _convert_kitsu_system_settings(ayon_settings, output):
    kitsu_settings = output["modules"]["kitsu"]
    kitsu_settings["server"] = ayon_settings["kitsu"]["server"]


def _convert_ftrack_system_settings(ayon_settings, output):
    # TODO implement and convert rest of ftrack settings
    ftrack_settings = output["modules"]["ftrack"]
    ayon_ftrack = ayon_settings["ftrack"]
    ftrack_settings["ftrack_server"] = ayon_ftrack["ftrack_server"]


def _convert_shotgrid_system_settings(ayon_settings, output):
    ayon_shotgrid = ayon_settings["shotgrid"]
    # Skip conversion if different ayon addon is used
    if "leecher_manager_url" not in ayon_shotgrid:
        return

    shotgrid_settings = output["modules"]["shotgrid"]
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


def _convert_timers_manager(ayon_settings, output):
    manager_settings = output["modules"]["timers_manager"]
    ayon_manager = ayon_settings["timers_manager"]
    for key in {
        "auto_stop", "full_time", "message_time", "disregard_publishing"
    }:
        manager_settings[key] = ayon_manager[key]


def _convert_clockify(ayon_settings, output):
    clockify_settings = output["modules"]["clockify"]
    ayon_clockify = ayon_settings["clockify"]
    for key in {
        "worskpace_name",
    }:
        clockify_settings[key] = ayon_clockify[key]


def _convert_deadline(ayon_settings, output):
    deadline_settings = output["modules"]["deadline"]
    ayon_deadline = ayon_settings["deadline"]
    deadline_urls = {}
    for item in ayon_deadline["deadline_urls"]:
        deadline_urls[item["name"]] = item["value"]
    deadline_settings["deadline_urls"] = deadline_urls


def _convert_muster(ayon_settings, output):
    muster_settings = output["modules"]["muster"]
    ayon_muster = ayon_settings["muster"]
    templates_mapping = {}
    for item in ayon_muster["templates_mapping"]:
        templates_mapping[item["name"]] = item["value"]
    muster_settings["templates_mapping"] = templates_mapping
    muster_settings["MUSTER_REST_URL"] = ayon_muster["MUSTER_REST_URL"]


def _convert_royalrender(ayon_settings, output):
    royalrender_settings = output["modules"]["royalrender"]
    ayon_royalrender = ayon_settings["royalrender"]
    royalrender_settings["rr_paths"] = {
        item["name"]: item["value"]
        for item in ayon_royalrender["rr_paths"]
    }


def _convert_modules(ayon_settings, output, addon_versions):
    # TODO add all modules
    # TODO add 'enabled' values
    for key, func in (
        ("kitsu", _convert_kitsu_system_settings),
        ("ftrack", _convert_ftrack_system_settings),
        ("shotgrid", _convert_shotgrid_system_settings),
        ("timers_manager", _convert_timers_manager),
        ("clockify", _convert_clockify),
        ("deadline", _convert_deadline),
        ("muster", _convert_muster),
        ("royalrender", _convert_royalrender),
    ):
        if key in ayon_settings:
            func(ayon_settings, output)

    for module_name, value in output["modules"].items():
        if "enabled" not in value:
            continue
        value["enabled"] = module_name in addon_versions

    # Missing modules conversions
    # - "sync_server" -> renamed to sitesync
    # - "slack" -> only 'enabled'
    # - "job_queue" -> completelly missing in ayon


def convert_system_settings(ayon_settings, default_settings, addon_versions):
    output = copy.deepcopy(default_settings)
    if "applications" in ayon_settings:
        _convert_applications(ayon_settings, output, False)

    if "core" in ayon_settings:
        _convert_general(ayon_settings, output)

    _convert_modules(ayon_settings, output, addon_versions)
    return output


# --------- Project settings ---------
def _convert_blender_project_settings(ayon_settings, output):
    if "blender" not in ayon_settings:
        return
    ayon_blender = ayon_settings["blender"]
    blender_settings = output["blender"]
    _convert_host_imageio(ayon_blender)

    ayon_workfile_build = ayon_blender["workfile_builder"]
    blender_workfile_build = blender_settings["workfile_builder"]
    for key in ("create_first_version", "custom_templates"):
        blender_workfile_build[key] = ayon_workfile_build[key]

    ayon_publish = ayon_blender["publish"]
    model_validators = ayon_publish.pop("model_validators", None)
    if model_validators is not None:
        for src_key, dst_key in (
            ("validate_mesh_has_uvs", "ValidateMeshHasUvs"),
            ("validate_mesh_no_negative_scale", "ValidateMeshNoNegativeScale"),
            ("validate_transform_zero", "ValidateTransformZero"),
        ):
            ayon_publish[dst_key] = model_validators.pop(src_key)

    blender_publish = blender_settings["publish"]
    for key in tuple(ayon_publish.keys()):
        blender_publish[key] = ayon_publish[key]


def _convert_celaction_project_settings(ayon_settings, output):
    if "celaction" not in ayon_settings:
        return
    ayon_celaction_publish = ayon_settings["celaction"]["publish"]
    celaction_publish_settings = output["celaction"]["publish"]

    output["celaction"]["imageio"] = _convert_host_imageio(
        ayon_celaction_publish
    )

    for plugin_name in tuple(celaction_publish_settings.keys()):
        if plugin_name in ayon_celaction_publish:
            celaction_publish_settings[plugin_name] = (
                ayon_celaction_publish[plugin_name]
            )


def _convert_flame_project_settings(ayon_settings, output):
    if "flame" not in ayon_settings:
        return

    ayon_flame = ayon_settings["flame"]
    flame_settings = output["flame"]
    flame_settings["create"] = ayon_flame["create"]

    ayon_load_flame = ayon_flame["load"]
    load_flame_settings = flame_settings["load"]
    # Wrong settings model on server side
    for src_key, dst_key in (
        ("load_clip", "LoadClip"),
        ("load_clip_batch", "LoadClipBatch"),
    ):
        if src_key in ayon_load_flame:
            ayon_load_flame[dst_key] = ayon_load_flame.pop(src_key)

    for plugin_name in tuple(load_flame_settings.keys()):
        if plugin_name in ayon_load_flame:
            load_flame_settings[plugin_name] = ayon_load_flame[plugin_name]

    ayon_publish_flame = ayon_flame["publish"]
    flame_publish_settings = flame_settings["publish"]
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
    for plugin_name in tuple(flame_publish_settings.keys()):
        if plugin_name in ayon_publish_flame:
            flame_publish_settings[plugin_name] = (
                ayon_publish_flame[plugin_name]
            )

    # 'imageio' changed model
    # - missing subkey 'project' which is in root of 'imageio' model
    _convert_host_imageio(ayon_flame)
    ayon_imageio_flame = ayon_flame["imageio"]
    if "project" not in ayon_imageio_flame:
        profile_mapping = ayon_imageio_flame.pop("profilesMapping")
        ayon_imageio_flame = {
            "project": ayon_imageio_flame,
            "profilesMapping": profile_mapping
        }
    flame_settings["imageio"] = ayon_imageio_flame


def _convert_fusion_project_settings(ayon_settings, output):
    if "fusion" not in ayon_settings:
        return
    ayon_fusion = ayon_settings["fusion"]
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

    _convert_host_imageio(ayon_imageio_fusion)

    imageio_fusion_settings = output["fusion"]["imageio"]
    for key in (
        "imageio",
    ):
        imageio_fusion_settings[key] = ayon_fusion[key]


def _convert_maya_project_settings(ayon_settings, output):
    if "maya" not in ayon_settings:
        return

    ayon_maya = ayon_settings["maya"]
    openpype_maya = output["maya"]

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

    same_keys = {
        "imageio",
        "scriptsmenu",
        "templated_workfile_build",
        "load",
        "create",
        "publish",
        "mel_workspace",
        "ext_mapping",
        "workfile_build",
        "filters",
        "maya-dirmap",
        "RenderSettings",
    }
    for key in same_keys:
        openpype_maya[key] = ayon_maya[key]


def _convert_nuke_knobs(knobs):
    new_knobs = []
    for knob in knobs:
        knob_type = knob["type"]
        value = knob[knob_type]

        if knob_type == "boolean":
            knob_type = "bool"

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
    openpype_nuke = output["nuke"]

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
        name = item.pop("name")
        item["reformat_node_config"] = _convert_nuke_knobs(
            item["reformat_node_config"])
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

    # Store converted values to openpype values
    for key in (
        "scriptsmenu",
        "nuke-dirmap",
        "filters",
        "load",
        "create",
        "publish",
        "workfile_builder",
        "imageio",
    ):
        openpype_nuke[key] = ayon_nuke[key]


def _convert_hiero_project_settings(ayon_settings, output):
    if "hiero" not in ayon_settings:
        return

    ayon_hiero = ayon_settings["hiero"]
    openpype_hiero = output["hiero"]

    new_gui_filters = {}
    for item in ayon_hiero.pop("filters"):
        subvalue = {}
        key = item["name"]
        for subitem in item["value"]:
            subvalue[subitem["name"]] = subitem["value"]
        new_gui_filters[key] = subvalue
    ayon_hiero["filters"] = new_gui_filters

    _convert_host_imageio(ayon_hiero)

    for key in (
        "create",
        "filters",
        "imageio",
        "load",
        "publish",
        "scriptsmenu",
    ):
        openpype_hiero[key] = ayon_hiero[key]


def _convert_photoshop_project_settings(ayon_settings, output):
    if "photoshop" not in ayon_settings:
        return

    ayon_photoshop = ayon_settings["photoshop"]
    photoshop_settings = output["photoshop"]
    collect_review = ayon_photoshop["publish"]["CollectReview"]
    if "active" in collect_review:
        collect_review["publish"] = collect_review.pop("active")

    _convert_host_imageio(ayon_photoshop)

    for key in (
        "create",
        "publish",
        "workfile_builder",
        "imageio",
    ):
        photoshop_settings[key] = ayon_photoshop[key]


def _convert_tvpaint_project_settings(ayon_settings, output):
    if "tvpaint" not in ayon_settings:
        return
    ayon_tvpaint = ayon_settings["tvpaint"]
    tvpaint_settings = output["tvpaint"]

    _convert_host_imageio(ayon_tvpaint)

    for key in (
        "stop_timer_on_application_exit",
        "load",
        "workfile_builder",
        "imageio",
    ):
        tvpaint_settings[key] = ayon_tvpaint[key]

    filters = {}
    for item in ayon_tvpaint["filters"]:
        value = item["value"]
        try:
            value = json.loads(value)

        except ValueError:
            value = {}
        filters[item["name"]] = value
    tvpaint_settings["filters"] = filters

    ayon_publish_settings = ayon_tvpaint["publish"]
    tvpaint_publish_settings = tvpaint_settings["publish"]
    for plugin_name in ("CollectRenderScene", "ExtractConvertToEXR"):
        tvpaint_publish_settings[plugin_name] = (
            ayon_publish_settings[plugin_name]
        )

    for plugin_name in (
        "ValidateProjectSettings",
        "ValidateMarks",
        "ValidateStartFrame",
        "ValidateAssetName",
    ):
        ayon_value = ayon_publish_settings[plugin_name]
        tvpaint_value = tvpaint_publish_settings[plugin_name]
        for src_key, dst_key in (
            ("action_enabled", "optional"),
            ("action_enable", "active"),
        ):
            if src_key in ayon_value:
                tvpaint_value[dst_key] = ayon_value[src_key]

    review_color = ayon_publish_settings["ExtractSequence"]["review_bg"]
    tvpaint_publish_settings["ExtractSequence"]["review_bg"] = _convert_color(
        review_color
    )


def _convert_traypublisher_project_settings(ayon_settings, output):
    if "traypublisher" not in ayon_settings:
        return

    ayon_traypublisher = ayon_settings["traypublisher"]
    traypublisher_settings = output["traypublisher"]

    _convert_host_imageio(ayon_traypublisher)
    traypublisher_settings["imageio"] = ayon_traypublisher["imageio"]

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

    traypublisher_settings["editorial_creators"][
        "editorial_simple"
    ] = ayon_editorial_simple


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
    output["webpublisher"]["publish"] = ayon_publish
    output["webpublisher"]["imageio"] = ayon_webpublisher["imageio"]


def _convert_deadline_project_settings(ayon_settings, output):
    if "deadline" not in ayon_settings:
        return

    ayon_deadline = ayon_settings["deadline"]
    deadline_settings = output["deadline"]

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
    deadline_publish_settings = deadline_settings["publish"]
    for key in tuple(deadline_publish_settings.keys()):
        if key in ayon_deadline_publish:
            deadline_publish_settings[key] = ayon_deadline_publish[key]


def _convert_kitsu_project_settings(ayon_settings, output):
    if "kitsu" not in ayon_settings:
        return

    ayon_kitsu = ayon_settings["kitsu"]
    kitsu_settings = output["kitsu"]
    for key in tuple(kitsu_settings.keys()):
        if key in ayon_kitsu:
            kitsu_settings[key] = ayon_kitsu[key]


def _convert_shotgrid_project_settings(ayon_settings, output):
    if "shotgrid" not in ayon_settings:
        return

    ayon_shotgrid = ayon_settings["shotgrid"]
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

    shotgrid_settings = output["shotgrid"]
    for key in tuple(shotgrid_settings.keys()):
        if key in ayon_shotgrid:
            shotgrid_settings[key] = ayon_shotgrid[key]


def _convert_slack_project_settings(ayon_settings, output):
    if "slack" not in ayon_settings:
        return

    ayon_slack = ayon_settings["slack"]
    slack_settings = output["slack"]
    ayon_slack.pop("enabled", None)
    for profile in ayon_slack["publish"]["CollectSlackFamilies"]["profiles"]:
        profile["tasks"] = profile.pop("task_names")
        profile["subsets"] = profile.pop("subset_names")

    for key in tuple(slack_settings.keys()):
        if key in ayon_settings:
            slack_settings[key] = ayon_settings[key]


def _convert_global_project_settings(ayon_settings, output):
    if "core" not in ayon_settings:
        return

    ayon_core = ayon_settings["core"]
    global_settings = output["global"]

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

    global_publish = global_settings["publish"]
    ayon_integrate_hero = ayon_publish["IntegrateHeroVersion"]
    global_integrate_hero = global_publish["IntegrateHeroVersion"]
    for key, value in global_integrate_hero.items():
        if key not in ayon_integrate_hero:
            ayon_integrate_hero[key] = value

    ayon_cleanup = ayon_publish["CleanUp"]
    if "patterns" in ayon_cleanup:
        ayon_cleanup["paterns"] = ayon_cleanup.pop("patterns")

    for key in tuple(global_publish.keys()):
        if key in ayon_publish:
            global_publish[key] = ayon_publish[key]

    # Project root settings
    for json_key in ("project_folder_structure", "project_environments"):
        try:
            value = json.loads(ayon_core[json_key])
        except ValueError:
            value = {}
        global_publish[json_key] = value

    # Tools settings
    ayon_tools = ayon_core["tools"]
    global_tools = global_settings["tools"]
    ayon_create_tool = ayon_tools["creator"]
    new_smart_select_families = {
        item["name"]: item["task_names"]
        for item in ayon_create_tool["families_smart_select"]
    }
    ayon_create_tool["families_smart_select"] = new_smart_select_families
    global_tools["creator"] = ayon_create_tool

    ayon_loader_tool = ayon_tools["loader"]
    for profile in ayon_loader_tool["family_filter_profiles"]:
        if "template_publish_families" in profile:
            profile["filter_families"] = (
                profile.pop("template_publish_families")
            )
    global_tools["loader"] = ayon_loader_tool

    global_tools["publish"] = ayon_tools["publish"]


def convert_project_settings(ayon_settings, default_settings):
    # Missing settings
    # - standalonepublisher
    output = copy.deepcopy(default_settings)
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
    _convert_kitsu_project_settings(ayon_settings, output)
    _convert_shotgrid_project_settings(ayon_settings, output)
    _convert_slack_project_settings(ayon_settings, output)

    _convert_global_project_settings(ayon_settings, output)

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
            value = ayon_api.get_addons_settings(only_values=False)
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
