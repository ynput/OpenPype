import os
import sys
import json
import tempfile
import random
import string
from avalon import api
import pype
from pypeapp import execute
import pyblish.api
from pypeapp import Logger
from pprint import pformat
log = Logger().get_logger(__name__)

PUBLISH_PATHS = []

self = sys.modules[__name__]
self.dbcon = False


def set_context(dbcon_in, data, app):
    ''' Sets context for pyblish (must be done before pyblish is launched)
    :param project: Name of `Project` where instance should be published
    :type project: str
    :param asset: Name of `Asset` where instance should be published
    :type asset: str
    '''
    self.dbcon = dbcon_in
    S = self.dbcon.Session
    project = data["project"]
    os.environ["AVALON_PROJECT"] = project
    S["AVALON_PROJECT"] = project

    asset = data["asset"]
    os.environ["AVALON_ASSET"] = asset

    self.dbcon.install()
    av_project = self.dbcon.find_one({'type': 'project'})
    av_asset = self.dbcon.find_one({
        "type": 'asset',
        "name": asset
    })
    parents = av_asset['data']['parents']
    log.debug(f"__ session: {av_asset}")
    log.debug(f"__ session: {parents}")
    hierarchy = ''
    if parents and len(parents) > 0:
        hierarchy = os.path.sep.join(parents)
    self.dbcon.uninstall()

    os.environ["AVALON_TASK"] = data["task"]
    os.environ["AVALON_WORKDIR"] = data["workdir"]
    os.environ["AVALON_HIERARCHY"] = hierarchy
    os.environ["AVALON_PROJECTCODE"] = av_project['data'].get('code', '')
    os.environ["AVALON_APP"] = app

    self.dbcon.install()
    S["current_dir"] = os.path.normpath(os.getcwd())
    log.debug(f"__ session: {S}")

    self.dbcon.uninstall()


def run_publish(data, gui=True):
    # cli pyblish seems like better solution
    return cli_publish(data, gui)


def cli_publish(data, gui=True):
    self.dbcon.install()
    S = self.dbcon.Session
    # unregister previouse plugins
    pyblish.api.deregister_all_plugins()

    # Registers Global pyblish plugins
    pype.install()

    if data.get("publishPath"):
        PUBLISH_PATHS.append(data.get("publishPath"))

    # Registers AdobeCommunicator pyblish plugins
    for path in PUBLISH_PATHS:
        pyblish.api.register_plugin_path(path)

    project_plugins_paths = os.environ.get("PYPE_PROJECT_PLUGINS")
    project_name = os.environ["AVALON_PROJECT"]
    if project_plugins_paths and project_name:
        for path in project_plugins_paths.split(os.pathsep):
            if not path:
                continue
            plugin_path = os.path.join(path, project_name, "plugins")
            if os.path.exists(plugin_path):
                pyblish.api.register_plugin_path(plugin_path)
                api.register_plugin_path(api.Loader, plugin_path)
                api.register_plugin_path(api.Creator, plugin_path)

    if data.get("adobePublishJsonPathGet"):
        return_data_path = data.get("adobePublishJsonPathGet")
    else:
        # Create hash name folder in temp
        chars = "".join([random.choice(string.ascii_letters)
                         for i in range(15)])
        staging_dir = tempfile.mkdtemp(chars)

        # create json for return data
        return_data_path = (
            staging_dir + os.path.basename(staging_dir) + 'return.json'
        )

    if data.get("adobePublishJsonPathSend"):
        json_data_path = data.get("adobePublishJsonPathSend")
    else:
        # create also json and fill with data
        json_data_path = staging_dir + os.path.basename(staging_dir) + '.json'
        with open(json_data_path, 'w') as outfile:
            json.dump(data, outfile)

    args = [
        "-pp", os.pathsep.join(pyblish.api.registered_paths())
    ]

    if gui:
        args += ["gui"]

    envcopy = os.environ.copy()
    envcopy["PYBLISH_HOSTS"] = "adobecommunicator"
    envcopy["AC_PUBLISH_INPATH"] = json_data_path
    envcopy["AC_PUBLISH_OUTPATH"] = return_data_path
    envcopy["PYBLISH_GUI"] = "pyblish_lite"

    # print testing env
    for k, v in envcopy.items():
        if ("AVALON" in k) or ("PYPE" in k):
            log.debug(f"env: {k}: {v}")

    log.debug(f"__ session: {S}")

    while not execute(
            [sys.executable, "-u", "-m", "pyblish"] + args, env=envcopy):
        self.dbcon.uninstall()

        # check if data are returned back
        if os.path.exists(return_data_path):
            return {"return_data_path": return_data_path}
        else:
            return False
