import os
import logging
import platform
import getpass

from openpype.pipeline import (
    legacy_io,
    Anatomy
)
from openpype.lib import (
    StringTemplate,
    TemplateUnsolved,
)
from openpype.client import get_representation_parents

log = logging.getLogger(__name__)


def get_actions_by_name():
    from .action_plugin import discover_builder_plugins
    actions_by_name = {}
    for action in discover_builder_plugins():
        action_name = action.__name__
        if action_name in actions_by_name:
            raise KeyError(
                "Duplicated loader name {} !".format(action_name)
            )
        actions_by_name[action_name] = action
    return actions_by_name


def get_actions_by_family(family):
    """Return all actions by family"""
    from .action_plugin import discover_builder_plugins

    actions_by_family = {}
    for action in discover_builder_plugins():
        action_name = action.__name__
        if action_name in actions_by_family:
            raise KeyError(
                "Duplicated loader family {} !".format(action_name)
            )

        action_families_list = action.families
        if family in action_families_list:
            actions_by_family[action_name] = action
    return actions_by_family


def action_with_repre_context(
    Action, repre_context, name=None, namespace=None, options=None, **kwargs
):
    # Ensure options is a dictionary when no explicit options provided
    if options is None:
        options = kwargs.get("data", dict())  # "data" for backward compat

    assert isinstance(options, dict), "Options must be a dictionary"

    # Fallback to subset when name is None
    if name is None:
        name = repre_context["subset"]["name"]

    log.info(
        "Running '%s' on '%s'" % (
            Action.__name__, repre_context["asset"]["name"]
        )
    )

    loader = Action(repre_context)
    return loader.load(repre_context, name, namespace, options)


def get_representation_path_from_context(context):
    """Preparation wrapper using only context as a argument"""
    representation = context['representation']
    project_doc = context.get("project")
    root = None
    session_project = legacy_io.Session.get("AVALON_PROJECT")
    if project_doc and project_doc["name"] != session_project:
        anatomy = Anatomy(project_doc["name"])
        root = anatomy.roots

    return get_representation_path(representation, root)


def get_representation_path(representation, root=None, dbcon=None):
    """Get filename from representation document
    There are three ways of getting the path from representation which are
    tried in following sequence until successful.
    1. Get template from representation['data']['template'] and data from
       representation['context']. Then format template with the data.
    2. Get template from project['config'] and format it with default data set
    3. Get representation['data']['path'] and use it directly
    Args:
        representation(dict): representation document from the database
    Returns:
        str: fullpath of the representation
    """

    if dbcon is None:
        dbcon = legacy_io

    if root is None:
        from openpype.pipeline import registered_root

        root = registered_root()

    def path_from_represenation():
        try:
            template = representation["data"]["template"]
        except KeyError:
            return None

        try:
            context = representation["context"]
            context["root"] = root
            path = StringTemplate.format_strict_template(
                template, context
            )
            # Force replacing backslashes with forward slashed if not on
            #   windows
            if platform.system().lower() != "windows":
                path = path.replace("\\", "/")
        except (TemplateUnsolved, KeyError):
            # Template references unavailable data
            return None

        if not path:
            return path

        normalized_path = os.path.normpath(path)
        if os.path.exists(normalized_path):
            return normalized_path
        return path

    def path_from_config():
        try:
            project_name = dbcon.active_project()
            version_, subset, asset, project = get_representation_parents(
                project_name, representation
            )
        except ValueError:
            log.debug(
                "Representation %s wasn't found in database, "
                "like a bug" % representation["name"]
            )
            return None

        try:
            template = project["config"]["template"]["publish"]
        except KeyError:
            log.debug(
                "No template in project %s, "
                "likely a bug" % project["name"]
            )
            return None

        # default list() in get would not discover missing parents on asset
        parents = asset.get("data", {}).get("parents")
        if parents is not None:
            hierarchy = "/".join(parents)

        # Cannot fail, required members only
        data = {
            "root": root,
            "project": {
                "name": project["name"],
                "code": project.get("data", {}).get("code")
            },
            "asset": asset["name"],
            "hierarchy": hierarchy,
            "subset": subset["name"],
            "version": version_["name"],
            "representation": representation["name"],
            "family": representation.get("context", {}).get("family"),
            "user": dbcon.Session.get("AVALON_USER", getpass.getuser()),
            "app": dbcon.Session.get("AVALON_APP", ""),
            "task": dbcon.Session.get("AVALON_TASK", "")
        }

        try:
            template_obj = StringTemplate(template)
            path = str(template_obj.format(data))
            # Force replacing backslashes with forward slashed if not on
            #   windows
            if platform.system().lower() != "windows":
                path = path.replace("\\", "/")

        except KeyError as e:
            log.debug("Template references unavailable data: %s" % e)
            return None

        normalized_path = os.path.normpath(path)
        if os.path.exists(normalized_path):
            return normalized_path
        return path

    def path_from_data():
        if "path" not in representation["data"]:
            return None

        path = representation["data"]["path"]
        # Force replacing backslashes with forward slashed if not on
        #   windows
        if platform.system().lower() != "windows":
            path = path.replace("\\", "/")

        if os.path.exists(path):
            return os.path.normpath(path)

        dir_path, file_name = os.path.split(path)
        if not os.path.exists(dir_path):
            return

        base_name, ext = os.path.splitext(file_name)
        file_name_items = None
        if "#" in base_name:
            file_name_items = [part for part in base_name.split("#") if part]
        elif "%" in base_name:
            file_name_items = base_name.split("%")

        if not file_name_items:
            return

        filename_start = file_name_items[0]

        for _file in os.listdir(dir_path):
            if _file.startswith(filename_start) and _file.endswith(ext):
                return os.path.normpath(path)

    return (
        path_from_represenation() or
        path_from_config() or
        path_from_data()
    )
