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


class TemplateFillError(Exception):
    def __init__(self, msg=None):
        if not msg:
            msg = "Creator's subset name template is missing key value."
        super(TemplateFillError, self).__init__(msg)


def get_subset_name_template(
    project_name,
    family,
    task_name,
    task_type,
    host_name,
    default_template=None,
    project_settings=None
):
    """Get subset name template based on passed context.

    Args:
        project_name (str): Project on which the context lives.
        family (str): Family (subset type) for which the subset name is
            calculated.
        host_name (str): Name of host in which the subset name is calculated.
        task_name (str): Name of task in which context the subset is created.
        task_type (str): Type of task in which context the subset is created.
        default_template (Union[str, None]): Default template which is used if
            settings won't find any matching possitibility. Constant
            'DEFAULT_SUBSET_TEMPLATE' is used if not defined.
        project_settings (Union[Dict[str, Any], None]): Prepared settings for
            project. Settings are queried if not passed.
    """

    if project_settings is None:
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
    return template


def get_subset_name(
    family,
    variant,
    task_name,
    asset_doc,
    project_name=None,
    host_name=None,
    default_template=None,
    dynamic_data=None,
    project_settings=None,
    family_filter=None,
):
    """Calculate subset name based on passed context and OpenPype settings.

    Subst name templates are defined in `project_settings/global/tools/creator
    /subset_name_profiles` where are profiles with host name, family, task name
    and task type filters. If context does not match any profile then
    `DEFAULT_SUBSET_TEMPLATE` is used as default template.

    That's main reason why so many arguments are required to calculate subset
    name.

    Option to pass family filter was added for special cases when creator or
    automated publishing require special subset name template which would be
    hard to maintain using its family value.
        Why not just pass the right family? -> Family is also used as fill
            value and for filtering of publish plugins.

    Todos:
        Find better filtering options to avoid requirement of
            argument 'family_filter'.

    Args:
        family (str): Instance family.
        variant (str): In most of the cases it is user input during creation.
        task_name (str): Task name on which context is instance created.
        asset_doc (dict): Queried asset document with its tasks in data.
            Used to get task type.
        project_name (Optional[str]): Name of project on which is instance
            created. Important for project settings that are loaded.
        host_name (Optional[str]): One of filtering criteria for template
            profile filters.
        default_template (Optional[str]): Default template if any profile does
            not match passed context. Constant 'DEFAULT_SUBSET_TEMPLATE'
            is used if is not passed.
        dynamic_data (Optional[Dict[str, Any]]): Dynamic data specific for
            a creator which creates instance.
        project_settings (Optional[Union[Dict[str, Any]]]): Prepared settings
            for project. Settings are queried if not passed.
        family_filter (Optional[str]): Use different family for subset template
            filtering. Value of 'family' is used when not passed.

    Raises:
        TemplateFillError: If filled template contains placeholder key which is not
            collected.
    """

    if not family:
        return ""

    if not host_name:
        host_name = os.environ.get("AVALON_APP")

    # Use only last part of class family value split by dot (`.`)
    family = family.rsplit(".", 1)[-1]

    if project_name is None:
        project_name = legacy_io.Session["AVALON_PROJECT"]

    asset_tasks = asset_doc.get("data", {}).get("tasks") or {}
    task_info = asset_tasks.get(task_name) or {}
    task_type = task_info.get("type")

    template = get_subset_name_template(
        project_name,
        family_filter or family,
        task_name,
        task_type,
        host_name,
        default_template=default_template,
        project_settings=project_settings
    )
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

    try:
        return template.format(**prepare_template_data(fill_pairs))
    except KeyError as exp:
        raise TemplateFillError(
            "Value for {} key is missing in template '{}'."
            " Available values are {}".format(str(exp), template, fill_pairs)
        )
