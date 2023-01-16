import os
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
            _color_value.append(int(color_value[idx:idx+2], 16))
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
            color_value[3] = int(color_value[3] * 255)
    return color_value


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
        group_dynamic_labels[group_name] = group.pop("label")

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

        if not clear_metadata:
            group["__dynamic_keys_labels__"] = variant_dynamic_labels
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
    shotgrid_settings = output["modules"]["shotgrid"]
    ayon_shotgrid = ayon_settings["shotgrid"]
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
    for key in {"worskpace_name",}:
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
    rr_paths = {}
    for item in ayon_royalrender:
        rr_paths[item["name"]] = item["value"]
    royalrender_settings["rr_paths"] = rr_paths


def _convert_modules(ayon_settings, output):
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

    # Missing modules conversions
    # - "sync_server" -> renamed to sitesync
    # - "slack" -> only 'enabled'
    # - "job_queue" -> completelly missing in ayon


def convert_system_settings(ayon_settings, default_settings):
    output = copy.deepcopy(default_settings)
    if "applications" in ayon_settings:
        _convert_applications(ayon_settings, output, False)

    if "core" in ayon_settings:
        _convert_general(ayon_settings, output)

    _convert_modules(ayon_settings, output)
    return output


# --------- Project settings ---------
def _convert_blender_project_settings(ayon_settings, output):
    if "blender" not in ayon_settings:
        return
    ayon_blender = ayon_settings["blender"]
    blender_settings = output["blender"]

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
    for key in tuple(blender_publish.keys()):
        blender_publish[key] = ayon_publish[key]


def _convert_celaction_project_settings(ayon_settings, output):
    if "celaction" not in ayon_settings:
        return
    ayon_celaction_publish = ayon_settings["celaction"]["publish"]
    celaction_publish_settings = output["celaction"]["publish"]

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
    ayon_imageio_fusion = ayon_settings["fusion"]["imageio"]
    imageio_fusion_settings = output["fusion"]["imageio"]
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
    imageio_fusion_settings["ocio"] = ayon_imageio_fusion["ocio"]


def _convert_maya_project_settings(ayon_settings, output):
    if "maya" not in ayon_settings:
        return
    # TODO implement (maya's settings are missing on ayon server)


def _convert_nuke_project_settings(ayon_settings, output):
    if "nuke" not in ayon_settings:
        return
    # TODO implement (nuke's settings are missing on ayon server)


def _convert_photoshop_project_settings(ayon_settings, output):
    if "photoshop" not in ayon_settings:
        return

    ayon_photoshop = ayon_settings["photoshop"]
    photoshop_settings = output["photoshop"]
    collect_review = ayon_photoshop["publish"]["CollectReview"]
    if "active" in collect_review:
        collect_review["publish"] = collect_review.pop("active")

    for key in ("create", "publish", "workfile_builder"):
        photoshop_settings[key] = ayon_photoshop[key]


def _convert_tvpaint_project_settings(ayon_settings, output):
    if "tvpaint" not in ayon_settings:
        return
    ayon_tvpaint = ayon_settings["tvpaint"]
    tvpaint_settings = output["tvpaint"]
    for key in (
        "stop_timer_on_application_exit",
        "load",
        "workfile_builder",
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
            ("action_enable", "active")
        ):
            if src_key in ayon_value:
                tvpaint_value[dst_key] = ayon_value[src_key]

    review_color = ayon_publish_settings["ExtractSequence"]["review_bg"]
    tvpaint_publish_settings["ExtractSequence"]["review_bg"] = (
        _convert_color(review_color)
    )


def _convert_traypublisher_project_settings(ayon_settings, output):
    if "traypublisher" not in ayon_settings:
        return

    ayon_traypublisher = ayon_settings["traypublisher"]
    traypublisher_settings = output["traypublisher"]

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
            ayon_editorial_simple.pop("shot_subset_creator")
        )
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

    traypublisher_settings["editorial_creators"]["editorial_simple"] = (
        ayon_editorial_simple
    )


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
        item["name"]: item["value"]
        for item in nuke_submit.pop("limit_groups")
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
        "leecher_manager_url"
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
    ayon_slack.pop("enabled")
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

    ayon_workfiles_tool = ayon_tools["Workfiles"]
    for item in ayon_workfiles_tool["last_workfile_on_startup"]:
        item["tasks"] = item.pop("task_names")

    for item in ayon_workfiles_tool["open_workfile_tool_on_startup"]:
        item["tasks"] = item.pop("task_names")
    global_tools["Workfiles"] = ayon_workfiles_tool

    ayon_loader_tool = ayon_tools["loader"]
    for profile in ayon_loader_tool["family_filter_profiles"]:
        if "template_publish_families" in profile:
            profile["filter_families"] = profile.pop(
                "template_publish_families"
            )
    global_tools["loader"] = ayon_loader_tool

    global_tools["publish"] = ayon_tools["publish"]


def convert_project_settings(ayon_settings, default_settings):
    output = copy.deepcopy(default_settings)
    exact_match = {
        "aftereffects",
        "harmony",
        "houdini",
        "resolve",
        "unreal",
    }
    for key in exact_match:
        output[key] = ayon_settings[key]

    _convert_blender_project_settings(ayon_settings, output)
    _convert_celaction_project_settings(ayon_settings, output)
    _convert_flame_project_settings(ayon_settings, output)
    _convert_fusion_project_settings(ayon_settings, output)
    # _convert_maya_project_settings(ayon_settings, output)
    # _convert_nuke_project_settings(ayon_settings, output)
    _convert_photoshop_project_settings(ayon_settings, output)
    _convert_tvpaint_project_settings(ayon_settings, output)
    _convert_traypublisher_project_settings(ayon_settings, output)

    _convert_deadline_project_settings(ayon_settings, output)
    _convert_kitsu_project_settings(ayon_settings, output)
    _convert_shotgrid_project_settings(ayon_settings, output)
    _convert_slack_project_settings(ayon_settings, output)

    _convert_global_project_settings(ayon_settings, output)
    not_available = {
        "webpublisher",
        "hiero",
        "standalonepublisher",
    }

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


class AyonSettingsCahe:
    _cache_by_project_name = {}
    _production_settings = None

    @classmethod
    def get_production_settings(cls):
        if (
            cls._production_settings is None
            or cls._production_settings.is_outdated
        ):
            value = ayon_api.get_full_production_settings()
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
            value = production_settings["settings"]
            for key, value in value.keys():
                value["enabled"] = key in addon_versions
            return value

        cache_item = cls._cache_by_project_name.get(project_name)
        if cache_item is None or cache_item.is_outdated:
            value = ayon_api.get_project_settings(project_name)
            if cache_item is None:
                cache_item = CacheItem(value)
                cls._cache_by_project_name[project_name] = cache_item
            else:
                cache_item.update_value(value)

        value = cache_item.get_value()
        for key, value in value.keys():
            value["enabled"] = key in addon_versions
        return value


def get_ayon_project_settings(default_values, project_name):
    ayon_settings = AyonSettingsCahe.get_value_by_project(project_name)
    return convert_project_settings(ayon_settings, default_values)


def get_ayon_system_settings(default_values):
    ayon_settings = AyonSettingsCahe.get_value_by_project(None)
    return convert_system_settings(ayon_settings, default_values)
