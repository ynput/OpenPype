import re

from openpype.pipeline import LoaderPlugin
from .launch_logic import stub
from openpype.pipeline import legacy_io
from openpype.client import get_asset_by_name
from openpype.settings import get_project_settings
from openpype.lib import prepare_template_data
from openpype.lib.profiles_filtering import filter_profiles


def get_unique_layer_name(layers, asset_name, subset_name):
    """
        Gets all layer names and if 'asset_name_subset_name' is present, it
        increases suffix by 1 (eg. creates unique layer name - for Loader)
    Args:
        layers (list) of dict with layers info (name, id etc.)
        asset_name (string):
        subset_name (string):

    Returns:
        (string): name_00X (without version)
    """
    name = "{}_{}".format(asset_name, subset_name)
    names = {}
    for layer in layers:
        layer_name = re.sub(r'_\d{3}$', '', layer.name)
        if layer_name in names.keys():
            names[layer_name] = names[layer_name] + 1
        else:
            names[layer_name] = 1
    occurrences = names.get(name, 0)

    return "{}_{:0>3d}".format(name, occurrences + 1)


class PhotoshopLoader(LoaderPlugin):
    @staticmethod
    def get_stub():
        return stub()


def get_subset_template(family):
    """Get subset template name from Settings"""
    project_name = legacy_io.Session["AVALON_PROJECT"]
    asset_name = legacy_io.Session["AVALON_ASSET"]
    task_name = legacy_io.Session["AVALON_TASK"]

    asset_doc = get_asset_by_name(
        project_name, asset_name, fields=["data.tasks"]
    )
    asset_tasks = asset_doc.get("data", {}).get("tasks") or {}
    task_info = asset_tasks.get(task_name) or {}
    task_type = task_info.get("type")

    tools_settings = get_project_settings(project_name)["global"]["tools"]
    profiles = tools_settings["creator"]["subset_name_profiles"]
    filtering_criteria = {
        "families": family,
        "hosts": "photoshop",
        "tasks": task_name,
        "task_types": task_type
    }

    matching_profile = filter_profiles(profiles, filtering_criteria)
    if matching_profile:
        return matching_profile["template"]


def get_subset_name_for_multiple(subset_name, subset_template, group,
                                 family, variant):
    """Update subset name with layer information to differentiate multiple

    subset_template might contain specific way how to format layer name
    ({layer},{Layer} or {LAYER}). If subset_template doesn't contain placeholder
    at all, fall back to original solution.
    """
    if not subset_template or 'layer' not in subset_template.lower():
        subset_name += group.name.title().replace(" ", "")
    else:
        fill_pairs = {
            "family": family,
            "variant": variant,
            "task": legacy_io.Session["AVALON_TASK"],
            "layer": group.name
        }

        return subset_template.format(**prepare_template_data(fill_pairs))
