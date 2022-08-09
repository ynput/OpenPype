from openpype.client import get_asset_by_name
from openpype.settings import get_project_settings
from openpype.lib import filter_profiles
from openpype.pipeline import Anatomy
from openpype.pipeline.template_data import get_template_data


def get_workfile_template_key_from_context(
    asset_name, task_name, host_name, project_name, project_settings=None
):
    """Helper function to get template key for workfile template.

    Do the same as `get_workfile_template_key` but returns value for "session
    context".

    It is required to pass one of 'dbcon' with already set project name or
    'project_name' arguments.

    Args:
        asset_name(str): Name of asset document.
        task_name(str): Task name for which is template key retrieved.
            Must be available on asset document under `data.tasks`.
        host_name(str): Name of host implementation for which is workfile
            used.
        project_name(str): Project name where asset and task is. Not required
            when 'dbcon' is passed.
        project_settings(Dict[str, Any]): Project settings for passed
            'project_name'. Not required at all but makes function faster.
    """

    asset_doc = get_asset_by_name(
        project_name, asset_name, fields=["data.tasks"]
    )
    asset_tasks = asset_doc.get("data", {}).get("tasks") or {}
    task_info = asset_tasks.get(task_name) or {}
    task_type = task_info.get("type")

    return get_workfile_template_key(
        task_type, host_name, project_name, project_settings
    )


def get_workfile_template_key(
    task_type, host_name, project_name, project_settings=None
):
    """Workfile template key which should be used to get workfile template.

    Function is using profiles from project settings to return right template
    for passet task type and host name.

    Args:
        task_type(str): Name of task type.
        host_name(str): Name of host implementation (e.g. "maya", "nuke", ...)
        project_name(str): Name of project in which context should look for
            settings.
        project_settings(Dict[str, Any]): Prepared project settings for
            project name. Optional to make processing faster.
    """

    default = "work"
    if not task_type or not host_name:
        return default

    if not project_settings:
        project_settings = get_project_settings(project_name)

    try:
        profiles = (
            project_settings
            ["global"]
            ["tools"]
            ["Workfiles"]
            ["workfile_template_profiles"]
        )
    except Exception:
        profiles = []

    if not profiles:
        return default

    profile_filter = {
        "task_types": task_type,
        "hosts": host_name
    }
    profile = filter_profiles(profiles, profile_filter)
    if profile:
        return profile["workfile_template"] or default
    return default


def get_workdir_with_workdir_data(
    workdir_data,
    project_name,
    anatomy=None,
    template_key=None,
    project_settings=None
):
    """Fill workdir path from entered data and project's anatomy.

    It is possible to pass only project's name instead of project's anatomy but
    one of them **must** be entered. It is preferred to enter anatomy if is
    available as initialization of a new Anatomy object may be time consuming.

    Args:
        workdir_data (Dict[str, Any]): Data to fill workdir template.
        project_name (str): Project's name.
            otherwise Anatomy object is created with using the project name.
        anatomy (Anatomy): Anatomy object for specific project. Faster
            processing if is passed.
        template_key (str): Key of work templates in anatomy templates. If not
            passed `get_workfile_template_key_from_context` is used to get it.
        project_settings(Dict[str, Any]): Prepared project settings for
            project name. Optional to make processing faster. Ans id used only
            if 'template_key' is not passed.

    Returns:
        TemplateResult: Workdir path.
    """

    if not anatomy:
        anatomy = Anatomy(project_name)

    if not template_key:
        template_key = get_workfile_template_key(
            workdir_data["task"]["type"],
            workdir_data["app"],
            workdir_data["project"]["name"],
            project_settings
        )

    anatomy_filled = anatomy.format(workdir_data)
    # Output is TemplateResult object which contain useful data
    output = anatomy_filled[template_key]["folder"]
    if output:
        return output.normalized()
    return output


def get_workdir(
    project_doc,
    asset_doc,
    task_name,
    host_name,
    anatomy=None,
    template_key=None,
    project_settings=None
):
    """Fill workdir path from entered data and project's anatomy.

    Args:
        project_doc (Dict[str, Any]): Mongo document of project from MongoDB.
        asset_doc (Dict[str, Any]): Mongo document of asset from MongoDB.
        task_name (str): Task name for which are workdir data preapred.
        host_name (str): Host which is used to workdir. This is required
            because workdir template may contain `{app}` key. In `Session`
            is stored under `AVALON_APP` key.
        anatomy (Anatomy): Optional argument. Anatomy object is created using
            project name from `project_doc`. It is preferred to pass this
            argument as initialization of a new Anatomy object may be time
            consuming.
        template_key (str): Key of work templates in anatomy templates. Default
            value is defined in `get_workdir_with_workdir_data`.
        project_settings(Dict[str, Any]): Prepared project settings for
            project name. Optional to make processing faster. Ans id used only
            if 'template_key' is not passed.

    Returns:
        TemplateResult: Workdir path.
    """

    if not anatomy:
        anatomy = Anatomy(project_doc["name"])

    workdir_data = get_template_data(
        project_doc, asset_doc, task_name, host_name
    )
    # Output is TemplateResult object which contain useful data
    return get_workdir_with_workdir_data(
        workdir_data,
        anatomy.project_name,
        anatomy,
        template_key,
        project_settings
    )
