from openpype.lib.profiles_filtering import filter_profiles
from openpype.settings import get_project_settings


def get_versioning_start(
    project_name,
    host_name,
    task_name=None,
    task_type=None,
    family=None,
    subset=None,
    project_settings=None,
):
    """Get anatomy versioning start"""
    if not project_settings:
        project_settings = get_project_settings(project_name)

    version_start = 1
    settings = project_settings["global"]
    profiles = settings.get("version_start_category", {}).get("profiles", [])

    if not profiles:
        return version_start

    filtering_criteria = {
        "host_names": host_name,
        "families": family,
        "task_names": task_name,
        "task_types": task_type,
        "subsets": subset
    }
    profile = filter_profiles(profiles, filtering_criteria)

    if profile is None:
        return version_start

    return profile["version_start"]
