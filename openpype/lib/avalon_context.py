"""Should be used only inside of hosts."""
import os
import json
import re
import copy
import platform
import logging
import collections
import functools
import getpass

from bson.objectid import ObjectId

from openpype.settings import (
    get_project_settings,
    get_system_settings
)
from .anatomy import Anatomy
from .profiles_filtering import filter_profiles
from .events import emit_event
from .path_templates import StringTemplate

# avalon module is not imported at the top
# - may not be in path at the time of pype.lib initialization
avalon = None

log = logging.getLogger("AvalonContext")


CURRENT_DOC_SCHEMAS = {
    "project": "openpype:project-3.0",
    "asset": "openpype:asset-3.0",
    "config": "openpype:config-2.0"
}
PROJECT_NAME_ALLOWED_SYMBOLS = "a-zA-Z0-9_"
PROJECT_NAME_REGEX = re.compile(
    "^[{}]+$".format(PROJECT_NAME_ALLOWED_SYMBOLS)
)


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
    """

    from openpype.settings import ProjectSettings, SaveWarningExc
    from avalon.api import AvalonMongoDB
    from avalon.schema import validate

    if dbcon is None:
        dbcon = AvalonMongoDB()

    if not PROJECT_NAME_REGEX.match(project_name):
        raise ValueError((
            "Project name \"{}\" contain invalid characters"
        ).format(project_name))

    database = dbcon.database
    project_doc = database[project_name].find_one(
        {"type": "project"},
        {"name": 1}
    )
    if project_doc:
        raise ValueError("Project with name \"{}\" already exists".format(
            project_name
        ))

    project_doc = {
        "type": "project",
        "name": project_name,
        "data": {
            "code": project_code,
            "library_project": library_project
        },
        "schema": CURRENT_DOC_SCHEMAS["project"]
    }
    # Insert document with basic data
    database[project_name].insert_one(project_doc)
    # Load ProjectSettings for the project and save it to store all attributes
    #   and Anatomy
    try:
        project_settings_entity = ProjectSettings(project_name)
        project_settings_entity.save()
    except SaveWarningExc as exc:
        print(str(exc))
    except Exception:
        database[project_name].delete_one({"type": "project"})
        raise

    project_doc = database[project_name].find_one({"type": "project"})

    try:
        # Validate created project document
        validate(project_doc)
    except Exception:
        # Remove project if is not valid
        database[project_name].delete_one({"type": "project"})
        raise

    return project_doc


def with_avalon(func):
    @functools.wraps(func)
    def wrap_avalon(*args, **kwargs):
        global avalon
        if avalon is None:
            import avalon
        return func(*args, **kwargs)
    return wrap_avalon


@with_avalon
def is_latest(representation):
    """Return whether the representation is from latest version

    Args:
        representation (dict): The representation document from the database.

    Returns:
        bool: Whether the representation is of latest version.

    """

    version = avalon.io.find_one({"_id": representation['parent']})
    if version["type"] == "hero_version":
        return True

    # Get highest version under the parent
    highest_version = avalon.io.find_one({
        "type": "version",
        "parent": version["parent"]
    }, sort=[("name", -1)], projection={"name": True})

    if version['name'] == highest_version['name']:
        return True
    else:
        return False


@with_avalon
def any_outdated():
    """Return whether the current scene has any outdated content"""

    checked = set()
    host = avalon.api.registered_host()
    for container in host.ls():
        representation = container['representation']
        if representation in checked:
            continue

        representation_doc = avalon.io.find_one(
            {
                "_id": ObjectId(representation),
                "type": "representation"
            },
            projection={"parent": True}
        )
        if representation_doc and not is_latest(representation_doc):
            return True
        elif not representation_doc:
            log.debug("Container '{objectName}' has an invalid "
                      "representation, it is missing in the "
                      "database".format(**container))

        checked.add(representation)

    return False


@with_avalon
def get_asset(asset_name=None):
    """ Returning asset document from database by its name.

        Doesn't count with duplicities on asset names!

        Args:
            asset_name (str)

        Returns:
            (MongoDB document)
    """
    if not asset_name:
        asset_name = avalon.api.Session["AVALON_ASSET"]

    asset_document = avalon.io.find_one({
        "name": asset_name,
        "type": "asset"
    })

    if not asset_document:
        raise TypeError("Entity \"{}\" was not found in DB".format(asset_name))

    return asset_document


@with_avalon
def get_hierarchy(asset_name=None):
    """
    Obtain asset hierarchy path string from mongo db

    Args:
        asset_name (str)

    Returns:
        (string): asset hierarchy path

    """
    if not asset_name:
        asset_name = avalon.io.Session.get(
            "AVALON_ASSET",
            os.environ["AVALON_ASSET"]
        )

    asset_entity = avalon.io.find_one({
        "type": 'asset',
        "name": asset_name
    })

    not_set = "PARENTS_NOT_SET"
    entity_parents = asset_entity.get("data", {}).get("parents", not_set)

    # If entity already have parents then just return joined
    if entity_parents != not_set:
        return "/".join(entity_parents)

    # Else query parents through visualParents and store result to entity
    hierarchy_items = []
    entity = asset_entity
    while True:
        parent_id = entity.get("data", {}).get("visualParent")
        if not parent_id:
            break
        entity = avalon.io.find_one({"_id": parent_id})
        hierarchy_items.append(entity["name"])

    # Add parents to entity data for next query
    entity_data = asset_entity.get("data", {})
    entity_data["parents"] = hierarchy_items
    avalon.io.update_many(
        {"_id": asset_entity["_id"]},
        {"$set": {"data": entity_data}}
    )

    return "/".join(hierarchy_items)


def get_system_general_anatomy_data():
    system_settings = get_system_settings()
    studio_name = system_settings["general"]["studio_name"]
    studio_code = system_settings["general"]["studio_code"]
    return {
        "studio": {
            "name": studio_name,
            "code": studio_code
        }
    }


def get_linked_asset_ids(asset_doc):
    """Return linked asset ids for `asset_doc` from DB

    Args:
        asset_doc (dict): Asset document from DB.

    Returns:
        (list): MongoDB ids of input links.
    """
    output = []
    if not asset_doc:
        return output

    input_links = asset_doc["data"].get("inputLinks") or []
    if input_links:
        for item in input_links:
            # Backwards compatibility for "_id" key which was replaced with
            #   "id"
            if "_id" in item:
                link_id = item["_id"]
            else:
                link_id = item["id"]
            output.append(link_id)

    return output


@with_avalon
def get_linked_assets(asset_doc):
    """Return linked assets for `asset_doc` from DB

    Args:
        asset_doc (dict): Asset document from DB

    Returns:
        (list) Asset documents of input links for passed asset doc.
    """
    link_ids = get_linked_asset_ids(asset_doc)
    if not link_ids:
        return []

    return list(avalon.io.find({"_id": {"$in": link_ids}}))


@with_avalon
def get_latest_version(asset_name, subset_name, dbcon=None, project_name=None):
    """Retrieve latest version from `asset_name`, and `subset_name`.

    Do not use if you want to query more than 5 latest versions as this method
    query 3 times to mongo for each call. For those cases is better to use
    more efficient way, e.g. with help of aggregations.

    Args:
        asset_name (str): Name of asset.
        subset_name (str): Name of subset.
        dbcon (avalon.mongodb.AvalonMongoDB, optional): Avalon Mongo connection
            with Session.
        project_name (str, optional): Find latest version in specific project.

    Returns:
        None: If asset, subset or version were not found.
        dict: Last version document for entered .
    """

    if not dbcon:
        log.debug("Using `avalon.io` for query.")
        dbcon = avalon.io
        # Make sure is installed
        dbcon.install()

    if project_name and project_name != dbcon.Session.get("AVALON_PROJECT"):
        # `avalon.io` has only `_database` attribute
        # but `AvalonMongoDB` has `database`
        database = getattr(dbcon, "database", dbcon._database)
        collection = database[project_name]
    else:
        project_name = dbcon.Session.get("AVALON_PROJECT")
        collection = dbcon

    log.debug((
        "Getting latest version for Project: \"{}\" Asset: \"{}\""
        " and Subset: \"{}\""
    ).format(project_name, asset_name, subset_name))

    # Query asset document id by asset name
    asset_doc = collection.find_one(
        {"type": "asset", "name": asset_name},
        {"_id": True}
    )
    if not asset_doc:
        log.info(
            "Asset \"{}\" was not found in Database.".format(asset_name)
        )
        return None

    subset_doc = collection.find_one(
        {"type": "subset", "name": subset_name, "parent": asset_doc["_id"]},
        {"_id": True}
    )
    if not subset_doc:
        log.info(
            "Subset \"{}\" was not found in Database.".format(subset_name)
        )
        return None

    version_doc = collection.find_one(
        {"type": "version", "parent": subset_doc["_id"]},
        sort=[("name", -1)],
    )
    if not version_doc:
        log.info(
            "Subset \"{}\" does not have any version yet.".format(subset_name)
        )
        return None
    return version_doc


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
    """
    if not dbcon:
        if not project_name:
            raise ValueError((
                "`get_workfile_template_key_from_context` requires to pass"
                " one of 'dbcon' or 'project_name' arguments."
            ))
        from avalon.api import AvalonMongoDB

        dbcon = AvalonMongoDB()
        dbcon.Session["AVALON_PROJECT"] = project_name

    elif not project_name:
        project_name = dbcon.Session["AVALON_PROJECT"]

    asset_doc = dbcon.find_one(
        {
            "type": "asset",
            "name": asset_name
        },
        {
            "data.tasks": 1
        }
    )
    asset_tasks = asset_doc.get("data", {}).get("tasks") or {}
    task_info = asset_tasks.get(task_name) or {}
    task_type = task_info.get("type")

    return get_workfile_template_key(
        task_type, host_name, project_name, project_settings
    )


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
    """
    default = "work"
    if not task_type or not host_name:
        return default

    if not project_settings:
        if not project_name:
            raise ValueError((
                "`get_workfile_template_key` requires to pass"
                " one of 'project_name' or 'project_settings' arguments."
            ))
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


# TODO rename function as is not just "work" specific
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
    """
    task_type = asset_doc['data']['tasks'].get(task_name, {}).get('type')

    project_task_types = project_doc["config"]["tasks"]
    task_code = project_task_types.get(task_type, {}).get("short_name")

    asset_parents = asset_doc["data"]["parents"]
    hierarchy = "/".join(asset_parents)

    parent_name = project_doc["name"]
    if asset_parents:
        parent_name = asset_parents[-1]

    data = {
        "project": {
            "name": project_doc["name"],
            "code": project_doc["data"].get("code")
        },
        "task": {
            "name": task_name,
            "type": task_type,
            "short": task_code,
        },
        "asset": asset_doc["name"],
        "parent": parent_name,
        "app": host_name,
        "user": getpass.getuser(),
        "hierarchy": hierarchy,
    }

    system_general_data = get_system_general_anatomy_data()
    data.update(system_general_data)

    return data


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
    """
    if not anatomy and not project_name:
        raise ValueError((
            "Missing required arguments one of `project_name` or `anatomy`"
            " must be entered."
        ))

    if not anatomy:
        anatomy = Anatomy(project_name)

    if not template_key:
        template_key = get_workfile_template_key(
            workdir_data["task"]["type"],
            workdir_data["app"],
            project_name=workdir_data["project"]["name"]
        )

    anatomy_filled = anatomy.format(workdir_data)
    # Output is TemplateResult object which contain useful data
    return anatomy_filled[template_key]["folder"]


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
    """
    if not anatomy:
        anatomy = Anatomy(project_doc["name"])

    workdir_data = get_workdir_data(
        project_doc, asset_doc, task_name, host_name
    )
    # Output is TemplateResult object which contain useful data
    return get_workdir_with_workdir_data(
        workdir_data, anatomy, template_key=template_key
    )


def template_data_from_session(session=None):
    """ Return dictionary with template from session keys.

    Args:
        session (dict, Optional): The Session to use. If not provided use the
            currently active global Session.
    Returns:
        dict: All available data from session.
    """
    from avalon import io
    import avalon.api

    if session is None:
        session = avalon.api.Session

    project_name = session["AVALON_PROJECT"]
    project_doc = io._database[project_name].find_one({"type": "project"})
    asset_doc = io._database[project_name].find_one({
        "type": "asset",
        "name": session["AVALON_ASSET"]
    })
    task_name = session["AVALON_TASK"]
    host_name = session["AVALON_APP"]
    return get_workdir_data(project_doc, asset_doc, task_name, host_name)


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

    """
    changes = dict()

    # If no changes, return directly
    if not any([task, asset, app]):
        return changes

    # Get asset document and asset
    asset_document = None
    asset_tasks = None
    if isinstance(asset, dict):
        # Assume asset database document
        asset_document = asset
        asset_tasks = asset_document.get("data", {}).get("tasks")
        asset = asset["name"]

    if not asset_document or not asset_tasks:
        from avalon import io

        # Assume asset name
        asset_document = io.find_one(
            {
                "name": asset,
                "type": "asset"
            },
            {"data.tasks": True}
        )
        assert asset_document, "Asset must exist"

    # Detect any changes compared session
    mapping = {
        "AVALON_ASSET": asset,
        "AVALON_TASK": task,
        "AVALON_APP": app,
    }
    changes = {
        key: value
        for key, value in mapping.items()
        if value and value != session.get(key)
    }
    if not changes:
        return changes

    # Compute work directory (with the temporary changed session so far)
    _session = session.copy()
    _session.update(changes)

    changes["AVALON_WORKDIR"] = get_workdir_from_session(_session)

    return changes


def get_workdir_from_session(session=None, template_key=None):
    import avalon.api

    if session is None:
        session = avalon.api.Session
    project_name = session["AVALON_PROJECT"]
    host_name = session["AVALON_APP"]
    anatomy = Anatomy(project_name)
    template_data = template_data_from_session(session)
    anatomy_filled = anatomy.format(template_data)

    if not template_key:
        task_type = template_data["task"]["type"]
        template_key = get_workfile_template_key(
            task_type,
            host_name,
            project_name=project_name
        )
    return anatomy_filled[template_key]["folder"]


def update_current_task(task=None, asset=None, app=None, template_key=None):
    """Update active Session to a new task work area.

    This updates the live Session to a different `asset`, `task` or `app`.

    Args:
        task (str): The task to set.
        asset (str): The asset to set.
        app (str): The app to set.

    Returns:
        dict: The changed key, values in the current Session.

    """
    import avalon.api

    changes = compute_session_changes(
        avalon.api.Session,
        task=task,
        asset=asset,
        app=app,
        template_key=template_key
    )

    # Update the Session and environments. Pop from environments all keys with
    # value set to None.
    for key, value in changes.items():
        avalon.api.Session[key] = value
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    # Emit session change
    emit_event("taskChanged", changes.copy())

    return changes


@with_avalon
def get_workfile_doc(asset_id, task_name, filename, dbcon=None):
    """Return workfile document for entered context.

    Do not use this method to get more than one document. In that cases use
    custom query as this will return documents from database one by one.

    Args:
        asset_id (ObjectId): Mongo ID of an asset under which workfile belongs.
        task_name (str): Name of task under which the workfile belongs.
        filename (str): Name of a workfile.
        dbcon (AvalonMongoDB): Optionally enter avalon AvalonMongoDB object and
            `avalon.io` is used if not entered.

    Returns:
        dict: Workfile document or None.
    """
    # Use avalon.io if dbcon is not entered
    if not dbcon:
        dbcon = avalon.io

    return dbcon.find_one({
        "type": "workfile",
        "parent": asset_id,
        "task_name": task_name,
        "filename": filename
    })


@with_avalon
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
            `avalon.io` is used if not entered.
    """
    # Use avalon.io if dbcon is not entered
    if not dbcon:
        dbcon = avalon.io

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
    project_doc = dbcon.find_one({"type": "project"})
    workdir_data = get_workdir_data(
        project_doc, asset_doc, task_name, dbcon.Session["AVALON_APP"]
    )
    # Prepare anatomy
    anatomy = Anatomy(project_doc["name"])
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


@with_avalon
def save_workfile_data_to_doc(workfile_doc, data, dbcon=None):
    if not workfile_doc:
        # TODO add log message
        return

    if not data:
        return

    # Use avalon.io if dbcon is not entered
    if not dbcon:
        dbcon = avalon.io

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


class BuildWorkfile:
    """Wrapper for build workfile process.

    Load representations for current context by build presets. Build presets
    are host related, since each host has it's loaders.
    """

    log = logging.getLogger("BuildWorkfile")

    @staticmethod
    def map_subsets_by_family(subsets):
        subsets_by_family = collections.defaultdict(list)
        for subset in subsets:
            family = subset["data"].get("family")
            if not family:
                families = subset["data"].get("families")
                if not families:
                    continue
                family = families[0]

            subsets_by_family[family].append(subset)
        return subsets_by_family

    def process(self):
        """Main method of this wrapper.

        Building of workfile is triggered and is possible to implement
        post processing of loaded containers if necessary.
        """
        containers = self.build_workfile()

        return containers

    @with_avalon
    def build_workfile(self):
        """Prepares and load containers into workfile.

        Loads latest versions of current and linked assets to workfile by logic
        stored in Workfile profiles from presets. Profiles are set by host,
        filtered by current task name and used by families.

        Each family can specify representation names and loaders for
        representations and first available and successful loaded
        representation is returned as container.

        At the end you'll get list of loaded containers per each asset.

        loaded_containers [{
            "asset_entity": <AssetEntity1>,
            "containers": [<Container1>, <Container2>, ...]
        }, {
            "asset_entity": <AssetEntity2>,
            "containers": [<Container3>, ...]
        }, {
            ...
        }]
        """
        from openpype.pipeline import discover_loader_plugins

        # Get current asset name and entity
        current_asset_name = avalon.io.Session["AVALON_ASSET"]
        current_asset_entity = avalon.io.find_one({
            "type": "asset",
            "name": current_asset_name
        })

        # Skip if asset was not found
        if not current_asset_entity:
            print("Asset entity with name `{}` was not found".format(
                current_asset_name
            ))
            return

        # Prepare available loaders
        loaders_by_name = {}
        for loader in discover_loader_plugins():
            loader_name = loader.__name__
            if loader_name in loaders_by_name:
                raise KeyError(
                    "Duplicated loader name {0}!".format(loader_name)
                )
            loaders_by_name[loader_name] = loader

        # Skip if there are any loaders
        if not loaders_by_name:
            self.log.warning("There are no registered loaders.")
            return

        # Get current task name
        current_task_name = avalon.io.Session["AVALON_TASK"]

        # Load workfile presets for task
        self.build_presets = self.get_build_presets(
            current_task_name, current_asset_entity
        )

        # Skip if there are any presets for task
        if not self.build_presets:
            self.log.warning(
                "Current task `{}` does not have any loading preset.".format(
                    current_task_name
                )
            )
            return

        # Get presets for loading current asset
        current_context_profiles = self.build_presets.get("current_context")
        # Get presets for loading linked assets
        link_context_profiles = self.build_presets.get("linked_assets")
        # Skip if both are missing
        if not current_context_profiles and not link_context_profiles:
            self.log.warning(
                "Current task `{}` has empty loading preset.".format(
                    current_task_name
                )
            )
            return

        elif not current_context_profiles:
            self.log.warning((
                "Current task `{}` doesn't have any loading"
                " preset for it's context."
            ).format(current_task_name))

        elif not link_context_profiles:
            self.log.warning((
                "Current task `{}` doesn't have any"
                "loading preset for it's linked assets."
            ).format(current_task_name))

        # Prepare assets to process by workfile presets
        assets = []
        current_asset_id = None
        if current_context_profiles:
            # Add current asset entity if preset has current context set
            assets.append(current_asset_entity)
            current_asset_id = current_asset_entity["_id"]

        if link_context_profiles:
            # Find and append linked assets if preset has set linked mapping
            link_assets = get_linked_assets(current_asset_entity)
            if link_assets:
                assets.extend(link_assets)

        # Skip if there are no assets. This can happen if only linked mapping
        # is set and there are no links for his asset.
        if not assets:
            self.log.warning(
                "Asset does not have linked assets. Nothing to process."
            )
            return

        # Prepare entities from database for assets
        prepared_entities = self._collect_last_version_repres(assets)

        # Load containers by prepared entities and presets
        loaded_containers = []
        # - Current asset containers
        if current_asset_id and current_asset_id in prepared_entities:
            current_context_data = prepared_entities.pop(current_asset_id)
            loaded_data = self.load_containers_by_asset_data(
                current_context_data, current_context_profiles, loaders_by_name
            )
            if loaded_data:
                loaded_containers.append(loaded_data)

        # - Linked assets container
        for linked_asset_data in prepared_entities.values():
            loaded_data = self.load_containers_by_asset_data(
                linked_asset_data, link_context_profiles, loaders_by_name
            )
            if loaded_data:
                loaded_containers.append(loaded_data)

        # Return list of loaded containers
        return loaded_containers

    @with_avalon
    def get_build_presets(self, task_name, asset_doc):
        """ Returns presets to build workfile for task name.

        Presets are loaded for current project set in
        io.Session["AVALON_PROJECT"], filtered by registered host
        and entered task name.

        Args:
            task_name (str): Task name used for filtering build presets.

        Returns:
            (dict): preset per entered task name
        """
        host_name = os.environ["AVALON_APP"]
        project_settings = get_project_settings(
            avalon.io.Session["AVALON_PROJECT"]
        )

        host_settings = project_settings.get(host_name) or {}
        # Get presets for host
        wb_settings = host_settings.get("workfile_builder")
        if not wb_settings:
            # backward compatibility
            wb_settings = host_settings.get("workfile_build") or {}

        builder_profiles = wb_settings.get("profiles")
        if not builder_profiles:
            return None

        task_type = (
            asset_doc
            .get("data", {})
            .get("tasks", {})
            .get(task_name, {})
            .get("type")
        )
        filter_data = {
            "task_types": task_type,
            "tasks": task_name
        }
        return filter_profiles(builder_profiles, filter_data)

    def _filter_build_profiles(self, build_profiles, loaders_by_name):
        """ Filter build profiles by loaders and prepare process data.

        Valid profile must have "loaders", "families" and "repre_names" keys
        with valid values.
        - "loaders" expects list of strings representing possible loaders.
        - "families" expects list of strings for filtering
                     by main subset family.
        - "repre_names" expects list of strings for filtering by
                        representation name.

        Lowered "families" and "repre_names" are prepared for each profile with
        all required keys.

        Args:
            build_profiles (dict): Profiles for building workfile.
            loaders_by_name (dict): Available loaders per name.

        Returns:
            (list): Filtered and prepared profiles.
        """
        valid_profiles = []
        for profile in build_profiles:
            # Check loaders
            profile_loaders = profile.get("loaders")
            if not profile_loaders:
                self.log.warning((
                    "Build profile has missing loaders configuration: {0}"
                ).format(json.dumps(profile, indent=4)))
                continue

            # Check if any loader is available
            loaders_match = False
            for loader_name in profile_loaders:
                if loader_name in loaders_by_name:
                    loaders_match = True
                    break

            if not loaders_match:
                self.log.warning((
                    "All loaders from Build profile are not available: {0}"
                ).format(json.dumps(profile, indent=4)))
                continue

            # Check families
            profile_families = profile.get("families")
            if not profile_families:
                self.log.warning((
                    "Build profile is missing families configuration: {0}"
                ).format(json.dumps(profile, indent=4)))
                continue

            # Check representation names
            profile_repre_names = profile.get("repre_names")
            if not profile_repre_names:
                self.log.warning((
                    "Build profile is missing"
                    " representation names filtering: {0}"
                ).format(json.dumps(profile, indent=4)))
                continue

            # Prepare lowered families and representation names
            profile["families_lowered"] = [
                fam.lower() for fam in profile_families
            ]
            profile["repre_names_lowered"] = [
                name.lower() for name in profile_repre_names
            ]

            valid_profiles.append(profile)

        return valid_profiles

    def _prepare_profile_for_subsets(self, subsets, profiles):
        """Select profile for each subset by it's data.

        Profiles are filtered for each subset individually.
        Profile is filtered by subset's family, optionally by name regex and
        representation names set in profile.
        It is possible to not find matching profile for subset, in that case
        subset is skipped and it is possible that none of subsets have
        matching profile.

        Args:
            subsets (list): Subset documents.
            profiles (dict): Build profiles.

        Returns:
            (dict) Profile by subset's id.
        """
        # Prepare subsets
        subsets_by_family = self.map_subsets_by_family(subsets)

        profiles_per_subset_id = {}
        for family, subsets in subsets_by_family.items():
            family_low = family.lower()
            for profile in profiles:
                # Skip profile if does not contain family
                if family_low not in profile["families_lowered"]:
                    continue

                # Precompile name filters as regexes
                profile_regexes = profile.get("subset_name_filters")
                if profile_regexes:
                    _profile_regexes = []
                    for regex in profile_regexes:
                        _profile_regexes.append(re.compile(regex))
                    profile_regexes = _profile_regexes

                # TODO prepare regex compilation
                for subset in subsets:
                    # Verify regex filtering (optional)
                    if profile_regexes:
                        valid = False
                        for pattern in profile_regexes:
                            if re.match(pattern, subset["name"]):
                                valid = True
                                break

                        if not valid:
                            continue

                    profiles_per_subset_id[subset["_id"]] = profile

                # break profiles loop on finding the first matching profile
                break
        return profiles_per_subset_id

    def load_containers_by_asset_data(
        self, asset_entity_data, build_profiles, loaders_by_name
    ):
        """Load containers for entered asset entity by Build profiles.

        Args:
            asset_entity_data (dict): Prepared data with subsets, last version
                and representations for specific asset.
            build_profiles (dict): Build profiles.
            loaders_by_name (dict): Available loaders per name.

        Returns:
            (dict) Output contains asset document and loaded containers.
        """

        # Make sure all data are not empty
        if not asset_entity_data or not build_profiles or not loaders_by_name:
            return

        asset_entity = asset_entity_data["asset_entity"]

        valid_profiles = self._filter_build_profiles(
            build_profiles, loaders_by_name
        )
        if not valid_profiles:
            self.log.warning(
                "There are not valid Workfile profiles. Skipping process."
            )
            return

        self.log.debug("Valid Workfile profiles: {}".format(valid_profiles))

        subsets_by_id = {}
        version_by_subset_id = {}
        repres_by_version_id = {}
        for subset_id, in_data in asset_entity_data["subsets"].items():
            subset_entity = in_data["subset_entity"]
            subsets_by_id[subset_entity["_id"]] = subset_entity

            version_data = in_data["version"]
            version_entity = version_data["version_entity"]
            version_by_subset_id[subset_id] = version_entity
            repres_by_version_id[version_entity["_id"]] = (
                version_data["repres"]
            )

        if not subsets_by_id:
            self.log.warning("There are not subsets for asset {0}".format(
                asset_entity["name"]
            ))
            return

        profiles_per_subset_id = self._prepare_profile_for_subsets(
            subsets_by_id.values(), valid_profiles
        )
        if not profiles_per_subset_id:
            self.log.warning("There are not valid subsets.")
            return

        valid_repres_by_subset_id = collections.defaultdict(list)
        for subset_id, profile in profiles_per_subset_id.items():
            profile_repre_names = profile["repre_names_lowered"]

            version_entity = version_by_subset_id[subset_id]
            version_id = version_entity["_id"]
            repres = repres_by_version_id[version_id]
            for repre in repres:
                repre_name_low = repre["name"].lower()
                if repre_name_low in profile_repre_names:
                    valid_repres_by_subset_id[subset_id].append(repre)

        # DEBUG message
        msg = "Valid representations for Asset: `{}`".format(
            asset_entity["name"]
        )
        for subset_id, repres in valid_repres_by_subset_id.items():
            subset = subsets_by_id[subset_id]
            msg += "\n# Subset Name/ID: `{}`/{}".format(
                subset["name"], subset_id
            )
            for repre in repres:
                msg += "\n## Repre name: `{}`".format(repre["name"])

        self.log.debug(msg)

        containers = self._load_containers(
            valid_repres_by_subset_id, subsets_by_id,
            profiles_per_subset_id, loaders_by_name
        )

        return {
            "asset_entity": asset_entity,
            "containers": containers
        }

    @with_avalon
    def _load_containers(
        self, repres_by_subset_id, subsets_by_id,
        profiles_per_subset_id, loaders_by_name
    ):
        """Real load by collected data happens here.

        Loading of representations per subset happens here. Each subset can
        loads one representation. Loading is tried in specific order.
        Representations are tried to load by names defined in configuration.
        If subset has representation matching representation name each loader
        is tried to load it until any is successful. If none of them was
        successful then next representation name is tried.
        Subset process loop ends when any representation is loaded or
        all matching representations were already tried.

        Args:
            repres_by_subset_id (dict): Available representations mapped
                by their parent (subset) id.
            subsets_by_id (dict): Subset documents mapped by their id.
            profiles_per_subset_id (dict): Build profiles mapped by subset id.
            loaders_by_name (dict): Available loaders per name.

        Returns:
            (list) Objects of loaded containers.
        """
        from openpype.pipeline import (
            IncompatibleLoaderError,
            load_container,
        )

        loaded_containers = []

        # Get subset id order from build presets.
        build_presets = self.build_presets.get("current_context", [])
        build_presets += self.build_presets.get("linked_assets", [])
        subset_ids_ordered = []
        for preset in build_presets:
            for preset_family in preset["families"]:
                for id, subset in subsets_by_id.items():
                    if preset_family not in subset["data"].get("families", []):
                        continue

                    subset_ids_ordered.append(id)

        # Order representations from subsets.
        print("repres_by_subset_id", repres_by_subset_id)
        representations_ordered = []
        representations = []
        for id in subset_ids_ordered:
            for subset_id, repres in repres_by_subset_id.items():
                if repres in representations:
                    continue

                if id == subset_id:
                    representations_ordered.append((subset_id, repres))
                    representations.append(repres)

        print("representations", representations)

        # Load ordered representations.
        for subset_id, repres in representations_ordered:
            subset_name = subsets_by_id[subset_id]["name"]

            profile = profiles_per_subset_id[subset_id]
            loaders_last_idx = len(profile["loaders"]) - 1
            repre_names_last_idx = len(profile["repre_names_lowered"]) - 1

            repre_by_low_name = {
                repre["name"].lower(): repre for repre in repres
            }

            is_loaded = False
            for repre_name_idx, profile_repre_name in enumerate(
                profile["repre_names_lowered"]
            ):
                # Break iteration if representation was already loaded
                if is_loaded:
                    break

                repre = repre_by_low_name.get(profile_repre_name)
                if not repre:
                    continue

                for loader_idx, loader_name in enumerate(profile["loaders"]):
                    if is_loaded:
                        break

                    loader = loaders_by_name.get(loader_name)
                    if not loader:
                        continue
                    try:
                        container = load_container(
                            loader,
                            repre["_id"],
                            name=subset_name
                        )
                        loaded_containers.append(container)
                        is_loaded = True

                    except Exception as exc:
                        if exc == IncompatibleLoaderError:
                            self.log.info((
                                "Loader `{}` is not compatible with"
                                " representation `{}`"
                            ).format(loader_name, repre["name"]))

                        else:
                            self.log.error(
                                "Unexpected error happened during loading",
                                exc_info=True
                            )

                        msg = "Loading failed."
                        if loader_idx < loaders_last_idx:
                            msg += " Trying next loader."
                        elif repre_name_idx < repre_names_last_idx:
                            msg += (
                                " Loading of subset `{}` was not successful."
                            ).format(subset_name)
                        else:
                            msg += " Trying next representation."
                        self.log.info(msg)

        return loaded_containers

    @with_avalon
    def _collect_last_version_repres(self, asset_entities):
        """Collect subsets, versions and representations for asset_entities.

        Args:
            asset_entities (list): Asset entities for which want to find data

        Returns:
            (dict): collected entities

        Example output:
        ```
        {
            {Asset ID}: {
                "asset_entity": <AssetEntity>,
                "subsets": {
                    {Subset ID}: {
                        "subset_entity": <SubsetEntity>,
                        "version": {
                            "version_entity": <VersionEntity>,
                            "repres": [
                                <RepreEntity1>, <RepreEntity2>, ...
                            ]
                        }
                    },
                    ...
                }
            },
            ...
        }
        output[asset_id]["subsets"][subset_id]["version"]["repres"]
        ```
        """

        if not asset_entities:
            return {}

        asset_entity_by_ids = {asset["_id"]: asset for asset in asset_entities}

        subsets = list(avalon.io.find({
            "type": "subset",
            "parent": {"$in": asset_entity_by_ids.keys()}
        }))
        subset_entity_by_ids = {subset["_id"]: subset for subset in subsets}

        sorted_versions = list(avalon.io.find({
            "type": "version",
            "parent": {"$in": subset_entity_by_ids.keys()}
        }).sort("name", -1))

        subset_id_with_latest_version = []
        last_versions_by_id = {}
        for version in sorted_versions:
            subset_id = version["parent"]
            if subset_id in subset_id_with_latest_version:
                continue
            subset_id_with_latest_version.append(subset_id)
            last_versions_by_id[version["_id"]] = version

        repres = avalon.io.find({
            "type": "representation",
            "parent": {"$in": last_versions_by_id.keys()}
        })

        output = {}
        for repre in repres:
            version_id = repre["parent"]
            version = last_versions_by_id[version_id]

            subset_id = version["parent"]
            subset = subset_entity_by_ids[subset_id]

            asset_id = subset["parent"]
            asset = asset_entity_by_ids[asset_id]

            if asset_id not in output:
                output[asset_id] = {
                    "asset_entity": asset,
                    "subsets": {}
                }

            if subset_id not in output[asset_id]["subsets"]:
                output[asset_id]["subsets"][subset_id] = {
                    "subset_entity": subset,
                    "version": {
                        "version_entity": version,
                        "repres": []
                    }
                }

            output[asset_id]["subsets"][subset_id]["version"]["repres"].append(
                repre
            )

        return output


@with_avalon
def get_creator_by_name(creator_name, case_sensitive=False):
    """Find creator plugin by name.

    Args:
        creator_name (str): Name of creator class that should be returned.
        case_sensitive (bool): Match of creator plugin name is case sensitive.
            Set to `False` by default.

    Returns:
        Creator: Return first matching plugin or `None`.
    """
    from openpype.pipeline import discover_legacy_creator_plugins

    # Lower input creator name if is not case sensitive
    if not case_sensitive:
        creator_name = creator_name.lower()

    for creator_plugin in discover_legacy_creator_plugins():
        _creator_name = creator_plugin.__name__

        # Lower creator plugin name if is not case sensitive
        if not case_sensitive:
            _creator_name = _creator_name.lower()

        if _creator_name == creator_name:
            return creator_plugin
    return None


@with_avalon
def change_timer_to_current_context():
    """Called after context change to change timers.

    TODO:
    - use TimersManager's static method instead of reimplementing it here
    """
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
        "project_name": avalon.io.Session["AVALON_PROJECT"],
        "asset_name": avalon.io.Session["AVALON_ASSET"],
        "task_name": avalon.io.Session["AVALON_TASK"]
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
    """

    if anatomy is None:
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
    """

    if dbcon is None:
        from avalon.api import AvalonMongoDB

        dbcon = AvalonMongoDB()

    dbcon.install()

    if dbcon.Session["AVALON_PROJECT"] != project_name:
        dbcon.Session["AVALON_PROJECT"] = project_name

    project_doc = dbcon.find_one(
        {"type": "project"},
        # All we need is "name" and "data.code" keys
        {
            "name": 1,
            "data.code": 1
        }
    )
    asset_doc = dbcon.find_one(
        {
            "type": "asset",
            "name": asset_name
        },
        # All we need is "name" and "data.tasks" keys
        {
            "name": 1,
            "data.tasks": 1
        }
    )

    return get_custom_workfile_template_by_context(
        template_profiles, project_doc, asset_doc, task_name, anatomy
    )


def get_custom_workfile_template(template_profiles):
    """Filter and fill workfile template profiles by current context.

    Current context is defined by `avalon.api.Session`. That's why this
    function should be used only inside host where context is set and stable.

    Args:
        template_profiles(list): Template profiles from settings.

    Returns:
        str: Path to template or None if none of profiles match current
            context. (Existence of formatted path is not validated.)
    """
    # Use `avalon.io` as Mongo connection
    from avalon import io

    return get_custom_workfile_template_by_string_context(
        template_profiles,
        io.Session["AVALON_PROJECT"],
        io.Session["AVALON_ASSET"],
        io.Session["AVALON_TASK"],
        io
    )


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
        fill_data(dict): Data for filling template.
        extensions(list, tuple): All allowed file extensions of workfile.
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
        filename = StringTemplate.format_strict_template(file_template, data)

    if full_path:
        return os.path.normpath(os.path.join(workdir, filename))

    return filename
