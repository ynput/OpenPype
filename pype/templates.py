import os
import re
import sys
from avalon import io, api as avalon, lib as avalonlib
from . import lib
# from pypeapp.api import (Templates, Logger, format)
from pypeapp import Logger, Anatomy
log = Logger().get_logger(__name__, os.getenv("AVALON_APP", "pype-config"))


self = sys.modules[__name__]
self.SESSION = None


def set_session():
    lib.set_io_database()
    self.SESSION = avalon.session


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


def get_context_data(
    project_name=None, hierarchy=None, asset=None, task_name=None
):
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
    if not task_name:
        if self.SESSION is None:
            set_session()
        task_name = self.SESSION.get("AVALON_TASK", None) \
            or os.getenv("AVALON_TASK", None)
        assert task_name, log.error(
            "missing `AVALON_TASK` in avalon session or os.environ!"
        )
    application = avalonlib.get_application(os.environ["AVALON_APP_NAME"])

    os.environ['AVALON_PROJECT'] = project_name
    io.Session['AVALON_PROJECT'] = project_name

    project_doc = io.find_one({"type": "project"})
    data = {
        "task": task_name,
        "asset": asset or get_asset(),
        "project": {
            "name": project_doc["name"],
            "code": project_doc["data"].get("code", '')
        },
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

    awd = self.SESSION.get("AVALON_WORKDIR", None) or \
        os.getenv("AVALON_WORKDIR", None)

    data = get_context_data(project, hierarchy, asset, task)

    if (not awd) or ("{" not in awd):
        awd = get_workdir_template(data)

    awd_filled = os.path.normpath(format(awd, data))

    self.SESSION["AVALON_WORKDIR"] = awd_filled
    os.environ["AVALON_WORKDIR"] = awd_filled
    log.info("`AVALON_WORKDIR` fixed to: {}".format(awd_filled))


def get_workdir_template(data=None):
    """
    Obtain workdir templated path from Anatomy()

    Args:
        data (dict, optional): basic contextual data

    Returns:
        string: template path
    """

    anatomy = Anatomy()
    anatomy_filled = anatomy.format(data or get_context_data())

    try:
        work = anatomy_filled["work"]
    except Exception as e:
        log.error("{0} Error in "
                  "get_workdir_template(): {1}".format(__name__, e))

    return work["folder"]
