import os
import re
from avalon import io
from avalon import api as avalon
from . import lib
from app.api import (Templates, Logger, format)
log = Logger.getLogger(__name__,
                       os.getenv("AVALON_APP", "pype-config"))

SESSION = avalon.session
if not SESSION:
    lib.set_io_database()


def load_data_from_templates():
    """
    Load Templates `contextual` data as singleton object
    [info](https://en.wikipedia.org/wiki/Singleton_pattern)

    Returns:
        singleton: adding data to sharable object variable

    """

    from . import api
    if not any([
        api.Dataflow,
        api.Anatomy,
        api.Colorspace,
        api.Metadata
    ]
    ):
        # base = Templates()
        t = Templates(type=["anatomy", "metadata", "dataflow", "colorspace"])
        api.Anatomy = t.anatomy
        api.Metadata = t.metadata.format()
        data = {"metadata": api.Metadata}
        api.Dataflow = t.dataflow.format(data)
        api.Colorspace = t.colorspace
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
    api.Metadata = None
    log.info("Data from templates were Unloaded...")


def get_version_from_workfile(file):
    """
    Finds version number in file path string

    Args:
        file (string): file path

    Returns:
        v: version number in string ('001')

    """
    pattern = re.compile(r"_v([0-9]*)")
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

    return io.find_one({"type": "project"})["data"]["code"]


def set_project_code(code):
    """
    Set project code into os.environ

    Args:
        code (string): project code

    Returns:
        os.environ[KEY]: project code
        avalon.sesion[KEY]: project code
    """
    SESSION["AVALON_PROJECTCODE"] = code
    os.environ["AVALON_PROJECTCODE"] = code


def get_project_name():
    """
    Obtain project name from environment variable

    Returns:
        string: project name

    """

    project_name = SESSION.get("AVALON_PROJECT", None) \
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
    asset = SESSION.get("AVALON_ASSET", None) \
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
    task = SESSION.get("AVALON_TASK", None) \
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
    hierarchy = io.find_one({
        "type": 'asset',
        "name": get_asset()}
    )['data']['parents']

    if hierarchy:
        # hierarchy = os.path.sep.join(hierarchy)
        return os.path.join(*hierarchy).replace("\\", "/")


def set_hierarchy(hierarchy):
    """
    Updates os.environ and session with asset hierarchy

    Args:
        hierarchy (string): hierarchy path ("silo/folder/seq")
    """
    SESSION["AVALON_HIERARCHY"] = hierarchy
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

    data = {
        "task": task or get_task(),
        "asset": asset or get_asset(),
        "project": {"name": project or get_project_name(),
                    "code": get_project_code()},
        "hierarchy": hierarchy or get_hierarchy(),
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
    awd = SESSION.get("AVALON_WORKDIR", None) \
        or os.getenv("AVALON_WORKDIR", None)
    data = get_context_data(project, hierarchy, asset, task)

    if (not awd) or ("{" not in awd):
        awd = get_workdir_template(data)

    awd_filled = os.path.normpath(format(awd, data))

    SESSION["AVALON_WORKDIR"] = awd_filled
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

    try:
        work = anatomy.work.format(data or get_context_data())
    except Exception as e:
        log.error("{0} Error in "
                  "get_workdir_template(): {1}".format(__name__, e))

    return os.path.join(work.root, work.folder)
