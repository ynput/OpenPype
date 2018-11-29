import os
import re
from avalon import io
from app.api import (Templates, Logger, format)
log = Logger.getLogger(__name__,
                       os.getenv("AVALON_APP", "pype-config"))


def load_data_from_templates():
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
    from . import api
    api.Dataflow = None
    api.Anatomy = None
    api.Colorspace = None
    api.Metadata = None
    log.info("Data from templates were Unloaded...")


def get_version_from_workfile(file):
    pattern = re.compile(r"_v([0-9]*)")
    try:
        v_string = pattern.findall(file)[0]
        return v_string
    except IndexError:
        log.error("templates:get_version_from_workfile:"
                  "`{}` missing version string."
                  "Example `v004`".format(file))


def get_project_code():
    return io.find_one({"type": "project"})["data"]["code"]


def get_project_name():
    project_name = os.getenv("AVALON_PROJECT", None)
    assert project_name, log.error("missing `AVALON_PROJECT`"
                                   "in environment variables")
    return project_name


def get_asset():
    asset = os.getenv("AVALON_ASSET", None)
    assert asset, log.error("missing `AVALON_ASSET`"
                            "in environment variables")
    return asset


def get_task():
    task = os.getenv("AVALON_TASK", None)
    assert task, log.error("missing `AVALON_TASK`"
                           "in environment variables")
    return task


def get_hiearchy():
    hierarchy = io.find_one({
        "type": 'asset',
        "name": get_asset()}
    )['data']['parents']

    if hierarchy:
        # hierarchy = os.path.sep.join(hierarchy)
        return os.path.join(*hierarchy)


def fill_avalon_workdir():
    awd = os.getenv("AVALON_WORKDIR", None)
    assert awd, log.error("missing `AVALON_WORKDIR`"
                          "in environment variables")
    if "{" not in awd:
        return

    data = {
        "hierarchy": get_hiearchy(),
        "task": get_task(),
        "asset": get_asset(),
        "project": {"name": get_project_name(),
                    "code": get_project_code()}}

    awd_filled = os.path.normpath(format(awd, data))
    os.environ["AVALON_WORKDIR"] = awd_filled
    log.info("`AVALON_WORKDIR` fixed to: {}".format(awd_filled))
