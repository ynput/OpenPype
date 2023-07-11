import os

from openpype.settings.lib import (
    get_default_project_settings, get_project_settings
)
from openpype.lib.profiles_filtering import filter_profiles


def get_versioning_start(
    host="", task_name="", task_type="", family="", subset=""
):
    """Get anatomy versioning start"""
    version_start = 1
    project_name = os.environ.get("AVALON_PROJECT")
    settings = None
    if project_name is None:
        settings = get_default_project_settings()
    else:
        settings = get_project_settings(project_name)

    settings = settings["global"]
    profiles = settings.get("version_start_category", {}).get("profiles", [])

    if not profiles:
        return version_start

    filtering_criteria = {
        "hosts": host,
        "families": family,
        "task_names": task_name,
        "task_types": task_type,
        "subsets": subset
    }
    profile = filter_profiles(profiles, filtering_criteria)

    if profile is None:
        return version_start

    return profile["version_start"]
