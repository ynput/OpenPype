import os

from openpype.settings import get_project_settings
from openpype.lib import filter_profiles, prepare_template_data
from openpype.pipeline import legacy_io

from .constants import DEFAULT_SUBSET_TEMPLATE


class TaskNotSetError(KeyError):
    def __init__(self, msg=None):
        if not msg:
            msg = "Creator's subset name template requires task name."
        super(TaskNotSetError, self).__init__(msg)


def get_subset_name(
    family,
    variant,
    task_name,
    asset_doc,
    project_name=None,
    host_name=None,
    default_template=None,
    dynamic_data=None,
    project_settings=None
):
    """Calculate subset name based on passed context and OpenPype settings.

    Subst name templates are defined in `project_settings/global/tools/creator
    /subset_name_profiles` where are profiles with host name, family, task name
    and task type filters. If context does not match any profile then
    `DEFAULT_SUBSET_TEMPLATE` is used as default template.

    That's main reason why so many arguments are required to calculate subset
    name.

    Args:
        family (str): Instance family.
        variant (str): In most of cases it is user input during creation.
        task_name (str): Task name on which context is instance created.
        asset_doc (dict): Queried asset document with it's tasks in data.
            Used to get task type.
        project_name (str): Name of project on which is instance created.
            Important for project settings that are loaded.
        host_name (str): One of filtering criteria for template profile
            filters.
        default_template (str): Default template if any profile does not match
            passed context. Constant 'DEFAULT_SUBSET_TEMPLATE' is used if
            is not passed.
        dynamic_data (dict): Dynamic data specific for a creator which creates
            instance.
        dbcon (AvalonMongoDB): Mongo connection to be able query asset document
            if 'asset_doc' is not passed.
    """

    if not family:
        return ""

    if not host_name:
        host_name = os.environ["AVALON_APP"]

    # Use only last part of class family value split by dot (`.`)
    family = family.rsplit(".", 1)[-1]

    if project_name is None:
        project_name = legacy_io.Session["AVALON_PROJECT"]

    asset_tasks = asset_doc.get("data", {}).get("tasks") or {}
    task_info = asset_tasks.get(task_name) or {}
    task_type = task_info.get("type")

    # Get settings
    if not project_settings:
        project_settings = get_project_settings(project_name)
    tools_settings = project_settings["global"]["tools"]
    profiles = tools_settings["creator"]["subset_name_profiles"]
    filtering_criteria = {
        "families": family,
        "hosts": host_name,
        "tasks": task_name,
        "task_types": task_type
    }

    matching_profile = filter_profiles(profiles, filtering_criteria)
    template = None
    if matching_profile:
        template = matching_profile["template"]

    # Make sure template is set (matching may have empty string)
    if not template:
        template = default_template or DEFAULT_SUBSET_TEMPLATE

    # Simple check of task name existence for template with {task} in
    #   - missing task should be possible only in Standalone publisher
    if not task_name and "{task" in template.lower():
        raise TaskNotSetError()

    fill_pairs = {
        "variant": variant,
        "family": family,
        "task": task_name
    }
    if dynamic_data:
        # Dynamic data may override default values
        for key, value in dynamic_data.items():
            fill_pairs[key] = value

    return template.format(**prepare_template_data(fill_pairs))
