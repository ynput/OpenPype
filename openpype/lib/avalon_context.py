"""Should be used only inside of hosts."""
import os
import copy
import platform
import logging
import functools
import warnings

import six

from openpype.client import (
    get_project,
    get_assets,
    get_asset_by_name,
    get_last_version_by_subset_name,
    get_workfile_info,
)
from openpype.client.operations import (
    CURRENT_ASSET_DOC_SCHEMA,
    CURRENT_PROJECT_SCHEMA,
    CURRENT_PROJECT_CONFIG_SCHEMA,
    PROJECT_NAME_ALLOWED_SYMBOLS,
    PROJECT_NAME_REGEX,
)
from .profiles_filtering import filter_profiles
from .path_templates import StringTemplate

legacy_io = None

log = logging.getLogger("AvalonContext")


# Backwards compatibility - should not be used anymore
#   - Will be removed in OP 3.16.*
CURRENT_DOC_SCHEMAS = {
    "project": CURRENT_PROJECT_SCHEMA,
    "asset": CURRENT_ASSET_DOC_SCHEMA,
    "config": CURRENT_PROJECT_CONFIG_SCHEMA
}


class AvalonContextDeprecatedWarning(DeprecationWarning):
    pass


def deprecated(new_destination):
    """Mark functions as deprecated.

    It will result in a warning being emitted when the function is used.
    """

    func = None
    if callable(new_destination):
        func = new_destination
        new_destination = None

    def _decorator(decorated_func):
        if new_destination is None:
            warning_message = (
                " Please check content of deprecated function to figure out"
                " possible replacement."
            )
        else:
            warning_message = " Please replace your usage with '{}'.".format(
                new_destination
            )

        @functools.wraps(decorated_func)
        def wrapper(*args, **kwargs):
            warnings.simplefilter("always", AvalonContextDeprecatedWarning)
            warnings.warn(
                (
                    "Call to deprecated function '{}'"
                    "\nFunction was moved or removed.{}"
                ).format(decorated_func.__name__, warning_message),
                category=AvalonContextDeprecatedWarning,
                stacklevel=4
            )
            return decorated_func(*args, **kwargs)
        return wrapper

    if func is None:
        return _decorator
    return _decorator(func)


@deprecated("openpype.client.operations.create_project")
def create_project(
    project_name, project_code, library_project=False, dbcon=None
):
    """Create project using OpenPype settings.

    This project creation function is not validating project document on
    creation. It is because project document is created blindly with only
    minimum required information about project which is it's name, code, type
    and schema.

    Entered project name must be unique and project must not exist yet.

    Args:
        project_name(str): New project name. Should be unique.
        project_code(str): Project's code should be unique too.
        library_project(bool): Project is library project.
        dbcon(AvalonMongoDB): Object of connection to MongoDB.

    Raises:
        ValueError: When project name already exists in MongoDB.

    Returns:
        dict: Created project document.

    Deprecated:
        Function will be removed after release version 3.16.*
    """

    from openpype.client.operations import create_project

    return create_project(project_name, project_code, library_project)


def with_pipeline_io(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        global legacy_io
        if legacy_io is None:
            from openpype.pipeline import legacy_io
        return func(*args, **kwargs)
    return wrapped


@deprecated("openpype.pipeline.context_tools.is_representation_from_latest")
def is_latest(representation):
    """Return whether the representation is from latest version

    Args:
        representation (dict): The representation document from the database.

    Returns:
        bool: Whether the representation is of latest version.

    Deprecated:
        Function will be removed after release version 3.15.*
    """

    from openpype.pipeline.context_tools import is_representation_from_latest

    return is_representation_from_latest(representation)


@deprecated("openpype.pipeline.load.any_outdated_containers")
def any_outdated():
    """Return whether the current scene has any outdated content.

    Deprecated:
        Function will be removed after release version 3.15.*
    """

    from openpype.pipeline.load import any_outdated_containers

    return any_outdated_containers()


@deprecated("openpype.pipeline.context_tools.get_current_project_asset")
def get_asset(asset_name=None):
    """ Returning asset document from database by its name.

    Doesn't count with duplicities on asset names!

    Args:
        asset_name (str)

    Returns:
        (MongoDB document)

    Deprecated:
        Function will be removed after release version 3.15.*
    """

    from openpype.pipeline.context_tools import get_current_project_asset

    return get_current_project_asset(asset_name=asset_name)


@deprecated("openpype.pipeline.template_data.get_general_template_data")
def get_system_general_anatomy_data(system_settings=None):
    """
    Deprecated:
        Function will be removed after release version 3.15.*
    """
    from openpype.pipeline.template_data import get_general_template_data

    return get_general_template_data(system_settings)


@deprecated("openpype.client.get_linked_asset_ids")
def get_linked_asset_ids(asset_doc):
    """Return linked asset ids for `asset_doc` from DB

    Args:
        asset_doc (dict): Asset document from DB.

    Returns:
        (list): MongoDB ids of input links.

    Deprecated:
        Function will be removed after release version 3.16.*
    """

    from openpype.client import get_linked_asset_ids
    from openpype.pipeline import legacy_io

    project_name = legacy_io.active_project()

    return get_linked_asset_ids(project_name, asset_doc=asset_doc)


@deprecated("openpype.client.get_linked_assets")
def get_linked_assets(asset_doc):
    """Return linked assets for `asset_doc` from DB

    Args:
        asset_doc (dict): Asset document from DB

    Returns:
        (list) Asset documents of input links for passed asset doc.

    Deprecated:
        Function will be removed after release version 3.15.*
    """

    from openpype.pipeline import legacy_io
    from openpype.client import get_linked_assets

    project_name = legacy_io.active_project()

    return get_linked_assets(project_name, asset_doc=asset_doc)


@deprecated("openpype.client.get_last_version_by_subset_name")
def get_latest_version(asset_name, subset_name, dbcon=None, project_name=None):
    """Retrieve latest version from `asset_name`, and `subset_name`.

    Do not use if you want to query more than 5 latest versions as this method
    query 3 times to mongo for each call. For those cases is better to use
    more efficient way, e.g. with help of aggregations.

    Args:
        asset_name (str): Name of asset.
        subset_name (str): Name of subset.
        dbcon (AvalonMongoDB, optional): Avalon Mongo connection with Session.
        project_name (str, optional): Find latest version in specific project.

    Returns:
        None: If asset, subset or version were not found.
        dict: Last version document for entered.

    Deprecated:
        Function will be removed after release version 3.15.*
    """

    if not project_name:
        if not dbcon:
            from openpype.pipeline import legacy_io

            log.debug("Using `legacy_io` for query.")
            dbcon = legacy_io
            # Make sure is installed
            dbcon.install()

        project_name = dbcon.active_project()

    return get_last_version_by_subset_name(
        project_name, subset_name, asset_name=asset_name
    )


@deprecated(
    "openpype.pipeline.workfile.get_workfile_template_key_from_context")
def get_workfile_template_key_from_context(
    asset_name, task_name, host_name, project_name=None,
    dbcon=None, project_settings=None
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
        dbcon(AvalonMongoDB): Connection to mongo with already set project
            under `AVALON_PROJECT`. Not required when 'project_name' is passed.
        project_settings(dict): Project settings for passed 'project_name'.
            Not required at all but makes function faster.
    Raises:
        ValueError: When both 'dbcon' and 'project_name' were not
            passed.

    Deprecated:
        Function will be removed after release version 3.16.*
    """

    from openpype.pipeline.workfile import (
        get_workfile_template_key_from_context
    )

    if not project_name:
        if not dbcon:
            raise ValueError((
                "`get_workfile_template_key_from_context` requires to pass"
                " one of 'dbcon' or 'project_name' arguments."
            ))
        project_name = dbcon.active_project()

    return get_workfile_template_key_from_context(
        asset_name, task_name, host_name, project_name, project_settings
    )


@deprecated(
    "openpype.pipeline.workfile.get_workfile_template_key")
def get_workfile_template_key(
    task_type, host_name, project_name=None, project_settings=None
):
    """Workfile template key which should be used to get workfile template.

    Function is using profiles from project settings to return right template
    for passet task type and host name.

    One of 'project_name' or 'project_settings' must be passed it is preferred
    to pass settings if are already available.

    Args:
        task_type(str): Name of task type.
        host_name(str): Name of host implementation (e.g. "maya", "nuke", ...)
        project_name(str): Name of project in which context should look for
            settings. Not required if `project_settings` are passed.
        project_settings(dict): Prepare project settings for project name.
            Not needed if `project_name` is passed.

    Raises:
        ValueError: When both 'project_name' and 'project_settings' were not
            passed.

    Deprecated:
        Function will be removed after release version 3.16.*
    """

    from openpype.pipeline.workfile import get_workfile_template_key

    return get_workfile_template_key(
        task_type, host_name, project_name, project_settings
    )


@deprecated("openpype.pipeline.template_data.get_template_data")
def get_workdir_data(project_doc, asset_doc, task_name, host_name):
    """Prepare data for workdir template filling from entered information.

    Args:
        project_doc (dict): Mongo document of project from MongoDB.
        asset_doc (dict): Mongo document of asset from MongoDB.
        task_name (str): Task name for which are workdir data preapred.
        host_name (str): Host which is used to workdir. This is required
            because workdir template may contain `{app}` key.

    Returns:
        dict: Data prepared for filling workdir template.

    Deprecated:
        Function will be removed after release version 3.15.*
    """

    from openpype.pipeline.template_data import get_template_data

    return get_template_data(
        project_doc, asset_doc, task_name, host_name
    )


@deprecated("openpype.pipeline.workfile.get_workdir_with_workdir_data")
def get_workdir_with_workdir_data(
    workdir_data, anatomy=None, project_name=None, template_key=None
):
    """Fill workdir path from entered data and project's anatomy.

    It is possible to pass only project's name instead of project's anatomy but
    one of them **must** be entered. It is preferred to enter anatomy if is
    available as initialization of a new Anatomy object may be time consuming.

    Args:
        workdir_data (dict): Data to fill workdir template.
        anatomy (Anatomy): Anatomy object for specific project. Optional if
            `project_name` is entered.
        project_name (str): Project's name. Optional if `anatomy` is entered
            otherwise Anatomy object is created with using the project name.
        template_key (str): Key of work templates in anatomy templates. If not
            passed `get_workfile_template_key_from_context` is used to get it.
        dbcon(AvalonMongoDB): Mongo connection. Required only if 'template_key'
            and 'project_name' are not passed.

    Returns:
        TemplateResult: Workdir path.

    Raises:
        ValueError: When both `anatomy` and `project_name` are set to None.

    Deprecated:
        Function will be removed after release version 3.15.*
    """

    if not anatomy and not project_name:
        raise ValueError((
            "Missing required arguments one of `project_name` or `anatomy`"
            " must be entered."
        ))

    if not project_name:
        project_name = anatomy.project_name

    from openpype.pipeline.workfile import get_workdir_with_workdir_data

    return get_workdir_with_workdir_data(
        workdir_data, project_name, anatomy, template_key
    )


@deprecated("openpype.pipeline.workfile.get_workdir_with_workdir_data")
def get_workdir(
    project_doc,
    asset_doc,
    task_name,
    host_name,
    anatomy=None,
    template_key=None
):
    """Fill workdir path from entered data and project's anatomy.

    Args:
        project_doc (dict): Mongo document of project from MongoDB.
        asset_doc (dict): Mongo document of asset from MongoDB.
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

    Returns:
        TemplateResult: Workdir path.

    Deprecated:
        Function will be removed after release version 3.15.*
    """

    from openpype.pipeline.workfile import get_workdir
    # Output is TemplateResult object which contain useful data
    return get_workdir(
        project_doc,
        asset_doc,
        task_name,
        host_name,
        anatomy,
        template_key
    )


@deprecated("openpype.pipeline.context_tools.get_template_data_from_session")
def template_data_from_session(session=None):
    """ Return dictionary with template from session keys.

    Args:
        session (dict, Optional): The Session to use. If not provided use the
            currently active global Session.

    Returns:
        dict: All available data from session.

    Deprecated:
        Function will be removed after release version 3.15.*
    """

    from openpype.pipeline.context_tools import get_template_data_from_session

    return get_template_data_from_session(session)


@deprecated("openpype.pipeline.context_tools.compute_session_changes")
def compute_session_changes(
    session, task=None, asset=None, app=None, template_key=None
):
    """Compute the changes for a Session object on asset, task or app switch

    This does *NOT* update the Session object, but returns the changes
    required for a valid update of the Session.

    Args:
        session (dict): The initial session to compute changes to.
            This is required for computing the full Work Directory, as that
            also depends on the values that haven't changed.
        task (str, Optional): Name of task to switch to.
        asset (str or dict, Optional): Name of asset to switch to.
            You can also directly provide the Asset dictionary as returned
            from the database to avoid an additional query. (optimization)
        app (str, Optional): Name of app to switch to.

    Returns:
        dict: The required changes in the Session dictionary.

    Deprecated:
        Function will be removed after release version 3.16.*
    """

    from openpype.pipeline import legacy_io
    from openpype.pipeline.context_tools import compute_session_changes

    if isinstance(asset, six.string_types):
        project_name = legacy_io.active_project()
        asset = get_asset_by_name(project_name, asset)

    return compute_session_changes(
        session,
        asset,
        task,
        template_key
    )


@deprecated("openpype.pipeline.context_tools.get_workdir_from_session")
def get_workdir_from_session(session=None, template_key=None):
    """Calculate workdir path based on session data.

    Args:
        session (Union[None, Dict[str, str]]): Session to use. If not passed
            current context session is used (from legacy_io).
        template_key (Union[str, None]): Precalculate template key to define
            workfile template name in Anatomy.

    Returns:
        str: Workdir path.

    Deprecated:
        Function will be removed after release version 3.16.*
    """

    from openpype.pipeline.context_tools import get_workdir_from_session

    return get_workdir_from_session(session, template_key)


@deprecated("openpype.pipeline.context_tools.change_current_context")
def update_current_task(task=None, asset=None, app=None, template_key=None):
    """Update active Session to a new task work area.

    This updates the live Session to a different `asset`, `task` or `app`.

    Args:
        task (str): The task to set.
        asset (str): The asset to set.
        app (str): The app to set.

    Returns:
        dict: The changed key, values in the current Session.

    Deprecated:
        Function will be removed after release version 3.16.*
    """

    from openpype.pipeline import legacy_io
    from openpype.pipeline.context_tools import change_current_context

    project_name = legacy_io.active_project()
    if isinstance(asset, six.string_types):
        asset = get_asset_by_name(project_name, asset)

    return change_current_context(asset, task, template_key)


@deprecated("openpype.client.get_workfile_info")
def get_workfile_doc(asset_id, task_name, filename, dbcon=None):
    """Return workfile document for entered context.

    Do not use this method to get more than one document. In that cases use
    custom query as this will return documents from database one by one.

    Args:
        asset_id (ObjectId): Mongo ID of an asset under which workfile belongs.
        task_name (str): Name of task under which the workfile belongs.
        filename (str): Name of a workfile.
        dbcon (AvalonMongoDB): Optionally enter avalon AvalonMongoDB object and
            `legacy_io` is used if not entered.

    Returns:
        dict: Workfile document or None.

    Deprecated:
        Function will be removed after release version 3.15.*
    """

    # Use legacy_io if dbcon is not entered
    if not dbcon:
        from openpype.pipeline import legacy_io
        dbcon = legacy_io

    project_name = dbcon.active_project()
    return get_workfile_info(project_name, asset_id, task_name, filename)


@deprecated
def create_workfile_doc(asset_doc, task_name, filename, workdir, dbcon=None):
    """Creates or replace workfile document in mongo.

    Do not use this method to update data. This method will remove all
    additional data from existing document.

    Args:
        asset_doc (dict): Document of asset under which workfile belongs.
        task_name (str): Name of task for which is workfile related to.
        filename (str): Filename of workfile.
        workdir (str): Path to directory where `filename` is located.
        dbcon (AvalonMongoDB): Optionally enter avalon AvalonMongoDB object and
            `legacy_io` is used if not entered.
    """

    from openpype.pipeline import Anatomy
    from openpype.pipeline.template_data import get_template_data

    # Use legacy_io if dbcon is not entered
    if not dbcon:
        from openpype.pipeline import legacy_io
        dbcon = legacy_io

    # Filter of workfile document
    doc_filter = {
        "type": "workfile",
        "parent": asset_doc["_id"],
        "task_name": task_name,
        "filename": filename
    }
    # Document data are copy of filter
    doc_data = copy.deepcopy(doc_filter)

    # Prepare project for workdir data
    project_name = dbcon.active_project()
    project_doc = get_project(project_name)
    workdir_data = get_template_data(
        project_doc, asset_doc, task_name, dbcon.Session["AVALON_APP"]
    )
    # Prepare anatomy
    anatomy = Anatomy(project_name)
    # Get workdir path (result is anatomy.TemplateResult)
    template_workdir = get_workdir_with_workdir_data(
        workdir_data, anatomy
    )
    template_workdir_path = str(template_workdir).replace("\\", "/")

    # Replace slashses in workdir path where workfile is located
    mod_workdir = workdir.replace("\\", "/")

    # Replace workdir from templates with rootless workdir
    rootles_workdir = mod_workdir.replace(
        template_workdir_path,
        template_workdir.rootless.replace("\\", "/")
    )

    doc_data["schema"] = "pype:workfile-1.0"
    doc_data["files"] = ["/".join([rootles_workdir, filename])]
    doc_data["data"] = {}

    dbcon.replace_one(
        doc_filter,
        doc_data,
        upsert=True
    )


@deprecated
def save_workfile_data_to_doc(workfile_doc, data, dbcon=None):
    if not workfile_doc:
        # TODO add log message
        return

    if not data:
        return

    # Use legacy_io if dbcon is not entered
    if not dbcon:
        from openpype.pipeline import legacy_io
        dbcon = legacy_io

    # Convert data to mongo modification keys/values
    # - this is naive implementation which does not expect nested
    #   dictionaries
    set_data = {}
    for key, value in data.items():
        new_key = "data.{}".format(key)
        set_data[new_key] = value

    # Update workfile document with data
    dbcon.update_one(
        {"_id": workfile_doc["_id"]},
        {"$set": set_data}
    )


@deprecated("openpype.pipeline.workfile.BuildWorkfile")
def BuildWorkfile():
    """Build workfile class was moved to workfile pipeline.

    Deprecated:
        Function will be removed after release version 3.16.*
    """
    from openpype.pipeline.workfile import BuildWorkfile

    return BuildWorkfile()


@deprecated("openpype.pipeline.create.get_legacy_creator_by_name")
def get_creator_by_name(creator_name, case_sensitive=False):
    """Find creator plugin by name.

    Args:
        creator_name (str): Name of creator class that should be returned.
        case_sensitive (bool): Match of creator plugin name is case sensitive.
            Set to `False` by default.

    Returns:
        Creator: Return first matching plugin or `None`.

    Deprecated:
        Function will be removed after release version 3.16.*
    """
    from openpype.pipeline.create import get_legacy_creator_by_name

    return get_legacy_creator_by_name(creator_name, case_sensitive)


@deprecated
def change_timer_to_current_context():
    """Called after context change to change timers.

    Deprecated:
        This method is specific for TimersManager module so please use the
        functionality from there. Function will be removed after release
        version 3.15.*
    """

    from openpype.pipeline import legacy_io

    webserver_url = os.environ.get("OPENPYPE_WEBSERVER_URL")
    if not webserver_url:
        log.warning("Couldn't find webserver url")
        return

    rest_api_url = "{}/timers_manager/start_timer".format(webserver_url)
    try:
        import requests
    except Exception:
        log.warning("Couldn't start timer")
        return
    data = {
        "project_name": legacy_io.Session["AVALON_PROJECT"],
        "asset_name": legacy_io.Session["AVALON_ASSET"],
        "task_name": legacy_io.Session["AVALON_TASK"]
    }

    requests.post(rest_api_url, json=data)


def _get_task_context_data_for_anatomy(
    project_doc, asset_doc, task_name, anatomy=None
):
    """Prepare Task context for anatomy data.

    WARNING: this data structure is currently used only in workfile templates.
        Key "task" is currently in rest of pipeline used as string with task
        name.

    Args:
        project_doc (dict): Project document with available "name" and
            "data.code" keys.
        asset_doc (dict): Asset document from MongoDB.
        task_name (str): Name of context task.
        anatomy (Anatomy): Optionally Anatomy for passed project name can be
            passed as Anatomy creation may be slow.

    Returns:
        dict: With Anatomy context data.
    """

    if anatomy is None:
        from openpype.pipeline import Anatomy
        anatomy = Anatomy(project_doc["name"])

    asset_name = asset_doc["name"]
    project_task_types = anatomy["tasks"]

    # get relevant task type from asset doc
    assert task_name in asset_doc["data"]["tasks"], (
        "Task name \"{}\" not found on asset \"{}\"".format(
            task_name, asset_name
        )
    )

    task_type = asset_doc["data"]["tasks"][task_name].get("type")

    assert task_type, (
        "Task name \"{}\" on asset \"{}\" does not have specified task type."
    ).format(asset_name, task_name)

    # get short name for task type defined in default anatomy settings
    project_task_type_data = project_task_types.get(task_type)
    assert project_task_type_data, (
        "Something went wrong. Default anatomy tasks are not holding"
        "requested task type: `{}`".format(task_type)
    )

    data = {
        "project": {
            "name": project_doc["name"],
            "code": project_doc["data"].get("code")
        },
        "asset": asset_name,
        "task": {
            "name": task_name,
            "type": task_type,
            "short": project_task_type_data["short_name"]
        }
    }

    system_general_data = get_system_general_anatomy_data()
    data.update(system_general_data)

    return data


@deprecated(
    "openpype.pipeline.workfile.get_custom_workfile_template_by_context")
def get_custom_workfile_template_by_context(
    template_profiles, project_doc, asset_doc, task_name, anatomy=None
):
    """Filter and fill workfile template profiles by passed context.

    It is expected that passed argument are already queried documents of
    project and asset as parents of processing task name.

    Existence of formatted path is not validated.

    Args:
        template_profiles(list): Template profiles from settings.
        project_doc(dict): Project document from MongoDB.
        asset_doc(dict): Asset document from MongoDB.
        task_name(str): Name of task for which templates are filtered.
        anatomy(Anatomy): Optionally passed anatomy object for passed project
            name.

    Returns:
        str: Path to template or None if none of profiles match current
            context. (Existence of formatted path is not validated.)

    Deprecated:
        Function will be removed after release version 3.16.*
    """

    if anatomy is None:
        from openpype.pipeline import Anatomy
        anatomy = Anatomy(project_doc["name"])

    # get project, asset, task anatomy context data
    anatomy_context_data = _get_task_context_data_for_anatomy(
        project_doc, asset_doc, task_name, anatomy
    )
    # add root dict
    anatomy_context_data["root"] = anatomy.roots

    # get task type for the task in context
    current_task_type = anatomy_context_data["task"]["type"]

    # get path from matching profile
    matching_item = filter_profiles(
        template_profiles,
        {"task_types": current_task_type}
    )
    # when path is available try to format it in case
    # there are some anatomy template strings
    if matching_item:
        template = matching_item["path"][platform.system().lower()]
        return StringTemplate.format_strict_template(
            template, anatomy_context_data
        )

    return None


@deprecated(
    "openpype.pipeline.workfile.get_custom_workfile_template_by_string_context"
)
def get_custom_workfile_template_by_string_context(
    template_profiles, project_name, asset_name, task_name,
    dbcon=None, anatomy=None
):
    """Filter and fill workfile template profiles by passed context.

    Passed context are string representations of project, asset and task.
    Function will query documents of project and asset to be able use
    `get_custom_workfile_template_by_context` for rest of logic.

    Args:
        template_profiles(list): Loaded workfile template profiles.
        project_name(str): Project name.
        asset_name(str): Asset name.
        task_name(str): Task name.
        dbcon(AvalonMongoDB): Optional avalon implementation of mongo
            connection with context Session.
        anatomy(Anatomy): Optionally prepared anatomy object for passed
            project.

    Returns:
        str: Path to template or None if none of profiles match current
            context. (Existence of formatted path is not validated.)

    Deprecated:
        Function will be removed after release version 3.16.*
    """

    project_name = None
    if anatomy is not None:
        project_name = anatomy.project_name

    if not project_name and dbcon is not None:
        project_name = dbcon.active_project()

    if not project_name:
        raise ValueError("Can't determina project")

    project_doc = get_project(project_name, fields=["name", "data.code"])
    asset_doc = get_asset_by_name(
        project_name, asset_name, fields=["name", "data.tasks"])

    return get_custom_workfile_template_by_context(
        template_profiles, project_doc, asset_doc, task_name, anatomy
    )


@deprecated("openpype.pipeline.context_tools.get_custom_workfile_template")
def get_custom_workfile_template(template_profiles):
    """Filter and fill workfile template profiles by current context.

    Current context is defined by `legacy_io.Session`. That's why this
    function should be used only inside host where context is set and stable.

    Args:
        template_profiles(list): Template profiles from settings.

    Returns:
        str: Path to template or None if none of profiles match current
            context. (Existence of formatted path is not validated.)

    Deprecated:
        Function will be removed after release version 3.16.*
    """

    from openpype.pipeline import legacy_io

    return get_custom_workfile_template_by_string_context(
        template_profiles,
        legacy_io.Session["AVALON_PROJECT"],
        legacy_io.Session["AVALON_ASSET"],
        legacy_io.Session["AVALON_TASK"],
        legacy_io
    )


@deprecated("openpype.pipeline.workfile.get_last_workfile_with_version")
def get_last_workfile_with_version(
    workdir, file_template, fill_data, extensions
):
    """Return last workfile version.

    Args:
        workdir(str): Path to dir where workfiles are stored.
        file_template(str): Template of file name.
        fill_data(dict): Data for filling template.
        extensions(list, tuple): All allowed file extensions of workfile.

    Returns:
        tuple: Last workfile<str> with version<int> if there is any otherwise
            returns (None, None).

    Deprecated:
        Function will be removed after release version 3.16.*
    """

    from openpype.pipeline.workfile import get_last_workfile_with_version

    return get_last_workfile_with_version(
        workdir, file_template, fill_data, extensions
    )


@deprecated("openpype.pipeline.workfile.get_last_workfile")
def get_last_workfile(
    workdir, file_template, fill_data, extensions, full_path=False
):
    """Return last workfile filename.

    Returns file with version 1 if there is not workfile yet.

    Args:
        workdir(str): Path to dir where workfiles are stored.
        file_template(str): Template of file name.
        fill_data(dict): Data for filling template.
        extensions(list, tuple): All allowed file extensions of workfile.
        full_path(bool): Full path to file is returned if set to True.

    Returns:
        str: Last or first workfile as filename of full path to filename.

    Deprecated:
        Function will be removed after release version 3.16.*
    """

    from openpype.pipeline.workfile import get_last_workfile

    return get_last_workfile(
        workdir, file_template, fill_data, extensions, full_path
    )


@deprecated("openpype.client.get_linked_ids_for_representations")
def get_linked_ids_for_representations(
    project_name, repre_ids, dbcon=None, link_type=None, max_depth=0
):
    """Returns list of linked ids of particular type (if provided).

    Goes from representations to version, back to representations
    Args:
        project_name (str)
        repre_ids (list) or (ObjectId)
        dbcon (avalon.mongodb.AvalonMongoDB, optional): Avalon Mongo connection
            with Session.
        link_type (str): ['reference', '..]
        max_depth (int): limit how many levels of recursion

    Returns:
        (list) of ObjectId - linked representations

    Deprecated:
        Function will be removed after release version 3.16.*
    """

    from openpype.client import get_linked_representation_ids

    if not isinstance(repre_ids, list):
        repre_ids = [repre_ids]

    output = []
    for repre_id in repre_ids:
        output.extend(get_linked_representation_ids(
            project_name,
            repre_id=repre_id,
            link_type=link_type,
            max_depth=max_depth
        ))
    return output
