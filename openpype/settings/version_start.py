import os

from openpype.settings.lib import (
    get_default_anatomy_settings, get_anatomy_settings
)
from openpype.lib.profiles_filtering import filter_profiles


def get_versioning_start(
    host_name="", task_name="", task_type="", families=[], subset=""
):
    """Get anatomy versioning start"""
    version_start = 1
    project_name = os.environ.get("AVALON_PROJECT")
    settings = None
    if project_name is None:
        settings = get_default_anatomy_settings()
    else:
        settings = get_anatomy_settings(project_name)

    defaults = settings["templates"]["defaults"]
    profiles = defaults.get("version_start_category", {}).get("profiles", [])

    if not profiles:
        return version_start

    filtering_criteria = {
        "hosts": host_name,
        "families": families,
        "task_names": task_name,
        "task_types": task_type,
        "subsets": subset
    }
    profile = filter_profiles(profiles, filtering_criteria)

    if profile is None:
        return version_start

    return profile["version_start"]
