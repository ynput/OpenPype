import os
import re
import copy
import platform

from openpype.client import get_asset_by_name
from openpype.settings import get_project_settings
from openpype.lib import filter_profiles, StringTemplate
from openpype.pipeline import Anatomy
from openpype.pipeline.template_data import get_template_data


def get_workfile_template_key_from_context(
    asset_name, task_name, host_name, project_name, project_settings=None
):
    """Helper function to get template key for workfile template.

    Do the same as `get_workfile_template_key` but returns value for "session
    context".

    Args:
        asset_name(str): Name of asset document.
        task_name(str): Task name for which is template key retrieved.
            Must be available on asset document under `data.tasks`.
        host_name(str): Name of host implementation for which is workfile
            used.
        project_name(str): Project name where asset and task is.
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


def get_last_workfile_with_version(
    workdir, file_template, fill_data, extensions
):
    """Return last workfile version.

    Args:
        workdir(str): Path to dir where workfiles are stored.
        file_template(str): Template of file name.
        fill_data(Dict[str, Any]): Data for filling template.
        extensions(Iterable[str]): All allowed file extensions of workfile.

    Returns:
        Tuple[Union[str, None], Union[int, None]]: Last workfile with version
            if there is any workfile otherwise None for both.
    """

    if not os.path.exists(workdir):
        return None, None

    # Fast match on extension
    filenames = [
        filename
        for filename in os.listdir(workdir)
        if os.path.splitext(filename)[1] in extensions
    ]

    # Build template without optionals, version to digits only regex
    # and comment to any definable value.
    _ext = []
    for ext in extensions:
        if not ext.startswith("."):
            ext = "." + ext
        # Escape dot for regex
        ext = "\\" + ext
        _ext.append(ext)
    ext_expression = "(?:" + "|".join(_ext) + ")"

    # Replace `.{ext}` with `{ext}` so we are sure there is not dot at the end
    file_template = re.sub(r"\.?{ext}", ext_expression, file_template)
    # Replace optional keys with optional content regex
    file_template = re.sub(r"<.*?>", r".*?", file_template)
    # Replace `{version}` with group regex
    file_template = re.sub(r"{version.*?}", r"([0-9]+)", file_template)
    file_template = re.sub(r"{comment.*?}", r".+?", file_template)
    file_template = StringTemplate.format_strict_template(
        file_template, fill_data
    )

    # Match with ignore case on Windows due to the Windows
    # OS not being case-sensitive. This avoids later running
    # into the error that the file did exist if it existed
    # with a different upper/lower-case.
    kwargs = {}
    if platform.system().lower() == "windows":
        kwargs["flags"] = re.IGNORECASE

    # Get highest version among existing matching files
    version = None
    output_filenames = []
    for filename in sorted(filenames):
        match = re.match(file_template, filename, **kwargs)
        if not match:
            continue

        file_version = int(match.group(1))
        if version is None or file_version > version:
            output_filenames[:] = []
            version = file_version

        if file_version == version:
            output_filenames.append(filename)

    output_filename = None
    if output_filenames:
        if len(output_filenames) == 1:
            output_filename = output_filenames[0]
        else:
            last_time = None
            for _output_filename in output_filenames:
                full_path = os.path.join(workdir, _output_filename)
                mod_time = os.path.getmtime(full_path)
                if last_time is None or last_time < mod_time:
                    output_filename = _output_filename
                    last_time = mod_time

    return output_filename, version


def get_last_workfile(
    workdir, file_template, fill_data, extensions, full_path=False
):
    """Return last workfile filename.

    Returns file with version 1 if there is not workfile yet.

    Args:
        workdir(str): Path to dir where workfiles are stored.
        file_template(str): Template of file name.
        fill_data(Dict[str, Any]): Data for filling template.
        extensions(Iterable[str]): All allowed file extensions of workfile.
        full_path(bool): Full path to file is returned if set to True.

    Returns:
        str: Last or first workfile as filename of full path to filename.
    """

    filename, version = get_last_workfile_with_version(
        workdir, file_template, fill_data, extensions
    )
    if filename is None:
        data = copy.deepcopy(fill_data)
        data["version"] = 1
        data.pop("comment", None)
        if not data.get("ext"):
            data["ext"] = extensions[0]
        data["ext"] = data["ext"].replace('.', '')
        filename = StringTemplate.format_strict_template(file_template, data)

    if full_path:
        return os.path.normpath(os.path.join(workdir, filename))

    return filename
