from openpype.lib.profiles_filtering import filter_profiles


def get_versioning_start(
    project_settings=None,
    host=None,
    task_name=None,
    task_type=None,
    family=None,
    subset=None
):
    """Get anatomy versioning start"""
    version_start = 1
    settings = project_settings["global"]
    profiles = settings.get("version_start_category", {}).get("profiles", [])

    if not profiles:
        return version_start

    filtering_criteria = {
        "host_names": host,
        "families": family,
        "task_names": task_name,
        "task_types": task_type,
        "subsets": subset
    }
    profile = filter_profiles(profiles, filtering_criteria)

    if profile is None:
        return version_start

    return profile["version_start"]
