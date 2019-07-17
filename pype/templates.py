import os
import re
import sys
from avalon import io, api as avalon, lib as avalonlib
from . import lib
# from pypeapp.api import (Templates, Logger, format)
from pypeapp import Logger, config, Anatomy
log = Logger().get_logger(__name__, os.getenv("AVALON_APP", "pype-config"))


self = sys.modules[__name__]
self.SESSION = None


def set_session():
    lib.set_io_database()
    self.SESSION = avalon.session


def load_data_from_templates():
    """
    Load Presets and Anatomy `contextual` data as singleton object
    [info](https://en.wikipedia.org/wiki/Singleton_pattern)

    Returns:
        singleton: adding data to sharable object variable

    """

    from . import api
    if not any([
        api.Dataflow,
        api.Anatomy,
        api.Colorspace
    ]
    ):
        presets = config.get_presets()
        anatomy = Anatomy()

        try:
            # try if it is not in projects custom directory
            # `{PYPE_PROJECT_CONFIGS}/[PROJECT_NAME]/init.json`
            # init.json define preset names to be used
            p_init = presets["init"]
            colorspace = presets["colorspace"][p_init["colorspace"]]
            dataflow = presets["dataflow"][p_init["dataflow"]]
        except KeyError:
            log.warning("No projects custom preset available...")
            colorspace = presets["colorspace"]["default"]
            dataflow = presets["dataflow"]["default"]
            log.info("Presets `colorspace` and `dataflow` loaded from `default`...")

        api.Anatomy = anatomy
        api.Dataflow = dataflow
        api.Colorspace = colorspace

        log.info("Data from templates were Loaded...")


def reset_data_from_templates():
    """
    Clear Templates `contextual` data from singleton
    object variable

    Returns:
        singleton: clearing data to None

    """

    from . import api
    api.Dataflow = None
    api.Anatomy = None
    api.Colorspace = None
    log.info("Data from templates were Unloaded...")


def get_version_from_path(file):
    """
    Finds version number in file path string

    Args:
        file (string): file path

    Returns:
        v: version number in string ('001')

    """
    pattern = re.compile(r"[\._]v([0-9]*)")
    try:
        v = pattern.findall(file)[0]
        return v
    except IndexError:
        log.error("templates:get_version_from_workfile:"
                  "`{}` missing version string."
                  "Example `v004`".format(file))


def get_project_code():
    """
    Obtain project code from database

    Returns:
        string: project code
    """

    return io.find_one({"type": "project"})["data"].get("code", '')


def set_project_code(code):
    """
    Set project code into os.environ

    Args:
        code (string): project code

    Returns:
        os.environ[KEY]: project code
        avalon.sesion[KEY]: project code
    """
    if self.SESSION is None:
        set_session()
    self.SESSION["AVALON_PROJECTCODE"] = code
    os.environ["AVALON_PROJECTCODE"] = code


def get_project_name():
    """
    Obtain project name from environment variable

    Returns:
        string: project name

    """
    if self.SESSION is None:
        set_session()
    project_name = self.SESSION.get("AVALON_PROJECT", None) \
        or os.getenv("AVALON_PROJECT", None)
    assert project_name, log.error("missing `AVALON_PROJECT`"
                                   "in avalon session "
                                   "or os.environ!")
    return project_name


def get_asset():
    """
    Obtain Asset string from session or environment variable

    Returns:
        string: asset name

    Raises:
        log: error
    """
    if self.SESSION is None:
        set_session()
    asset = self.SESSION.get("AVALON_ASSET", None) \
        or os.getenv("AVALON_ASSET", None)
    log.info("asset: {}".format(asset))
    assert asset, log.error("missing `AVALON_ASSET`"
                            "in avalon session "
                            "or os.environ!")
    return asset


def get_task():
    """
    Obtain Task string from session or environment variable

    Returns:
        string: task name

    Raises:
        log: error
    """
    if self.SESSION is None:
        set_session()
    task = self.SESSION.get("AVALON_TASK", None) \
        or os.getenv("AVALON_TASK", None)
    assert task, log.error("missing `AVALON_TASK`"
                           "in avalon session "
                           "or os.environ!")
    return task


def get_hierarchy():
    """
    Obtain asset hierarchy path string from mongo db

    Returns:
        string: asset hierarchy path

    """
    parents = io.find_one({
        "type": 'asset',
        "name": get_asset()}
    )['data']['parents']

    hierarchy = ""
    if parents and len(parents) > 0:
        # hierarchy = os.path.sep.join(hierarchy)
        hierarchy = os.path.join(*parents).replace("\\", "/")
    return hierarchy


def set_hierarchy(hierarchy):
    """
    Updates os.environ and session with asset hierarchy

    Args:
        hierarchy (string): hierarchy path ("silo/folder/seq")
    """
    if self.SESSION is None:
        set_session()
    self.SESSION["AVALON_HIERARCHY"] = hierarchy
    os.environ["AVALON_HIERARCHY"] = hierarchy


def get_context_data(project=None,
                     hierarchy=None,
                     asset=None,
                     task=None):
    """
    Collect all main contextual data

    Args:
        project (string, optional): project name
        hierarchy (string, optional): hierarchy path
        asset (string, optional): asset name
        task (string, optional): task name

    Returns:
        dict: contextual data

    """
    application = avalonlib.get_application(os.environ["AVALON_APP_NAME"])
    data = {
        "task": task or get_task(),
        "asset": asset or get_asset(),
        "project": {"name": project or get_project_name(),
                    "code": get_project_code()},
        "hierarchy": hierarchy or get_hierarchy(),
        "app": application["application_dir"]
    }
    return data


def set_avalon_workdir(project=None,
                       hierarchy=None,
                       asset=None,
                       task=None):
    """
    Updates os.environ and session with filled workdir

    Args:
        project (string, optional): project name
        hierarchy (string, optional): hierarchy path
        asset (string, optional): asset name
        task (string, optional): task name

    Returns:
        os.environ[AVALON_WORKDIR]: workdir path
        avalon.session[AVALON_WORKDIR]: workdir path

    """
    if self.SESSION is None:
        set_session()

    awd = self.SESSION.get("AVALON_WORKDIR", None) or os.getenv("AVALON_WORKDIR", None)
    data = get_context_data(project, hierarchy, asset, task)

    if (not awd) or ("{" not in awd):
        awd = get_workdir_template(data)

    awd_filled = os.path.normpath(format(awd, data))

    self.SESSION["AVALON_WORKDIR"] = awd_filled
    os.environ["AVALON_WORKDIR"] = awd_filled
    log.info("`AVALON_WORKDIR` fixed to: {}".format(awd_filled))


def get_workdir_template(data=None):
    """
    Obtain workdir templated path from api.Anatomy singleton

    Args:
        data (dict, optional): basic contextual data

    Returns:
        string: template path
    """
    from . import api

    """ Installs singleton data """
    load_data_from_templates()

    anatomy = api.Anatomy
    anatomy_filled = anatomy.format(data or get_context_data())

    try:
        work = anatomy_filled["work"]
    except Exception as e:
        log.error("{0} Error in "
                  "get_workdir_template(): {1}".format(__name__, e))

    return work["folder"]
