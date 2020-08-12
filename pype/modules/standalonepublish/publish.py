import os
import sys
import json
import tempfile
import random
import string

from avalon import io
import pype
from pype.api import execute, Logger

import pyblish.api


log = Logger().get_logger("standalonepublisher")


def set_context(project, asset, task, app):
    ''' Sets context for pyblish (must be done before pyblish is launched)
    :param project: Name of `Project` where instance should be published
    :type project: str
    :param asset: Name of `Asset` where instance should be published
    :type asset: str
    '''
    os.environ["AVALON_PROJECT"] = project
    io.Session["AVALON_PROJECT"] = project
    os.environ["AVALON_ASSET"] = asset
    io.Session["AVALON_ASSET"] = asset
    if not task:
        task = ''
    os.environ["AVALON_TASK"] = task
    io.Session["AVALON_TASK"] = task

    io.install()

    av_project = io.find_one({'type': 'project'})
    av_asset = io.find_one({
        "type": 'asset',
        "name": asset
    })

    parents = av_asset['data']['parents']
    hierarchy = ''
    if parents and len(parents) > 0:
        hierarchy = os.path.sep.join(parents)

    os.environ["AVALON_HIERARCHY"] = hierarchy
    io.Session["AVALON_HIERARCHY"] = hierarchy

    os.environ["AVALON_PROJECTCODE"] = av_project['data'].get('code', '')
    io.Session["AVALON_PROJECTCODE"] = av_project['data'].get('code', '')

    io.Session["current_dir"] = os.path.normpath(os.getcwd())

    os.environ["AVALON_APP"] = app
    io.Session["AVALON_APP"] = app

    io.uninstall()


def publish(data, gui=True):
    # cli pyblish seems like better solution
    return cli_publish(data, gui)


def cli_publish(data, gui=True):
    from . import PUBLISH_PATHS

    PUBLISH_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "publish.py")
    io.install()

    # Create hash name folder in temp
    chars = "".join([random.choice(string.ascii_letters) for i in range(15)])
    staging_dir = tempfile.mkdtemp(chars)

    # create also json and fill with data
    json_data_path = staging_dir + os.path.basename(staging_dir) + '.json'
    with open(json_data_path, 'w') as outfile:
        json.dump(data, outfile)

    envcopy = os.environ.copy()
    envcopy["PYBLISH_HOSTS"] = "standalonepublisher"
    envcopy["SAPUBLISH_INPATH"] = json_data_path
    envcopy["PYBLISHGUI"] = "pyblish_pype"
    envcopy["PUBLISH_PATHS"] = os.pathsep.join(PUBLISH_PATHS)
    if data.get("family", "").lower() == "editorial":
        envcopy["PYBLISH_SUSPEND_LOGS"] = "1"

    result = execute(
        [sys.executable, PUBLISH_SCRIPT_PATH],
        env=envcopy
    )

    result = {}
    if os.path.exists(json_data_path):
        with open(json_data_path, "r") as f:
            result = json.load(f)

    log.info(f"Publish result: {result}")

    io.uninstall()

    return False


def main(env):
    from avalon.tools import publish
    # Registers pype's Global pyblish plugins
    pype.install()

    # Register additional paths
    addition_paths_str = env.get("PUBLISH_PATHS") or ""
    addition_paths = addition_paths_str.split(os.pathsep)
    for path in addition_paths:
        path = os.path.normpath(path)
        if not os.path.exists(path):
            continue
        pyblish.api.register_plugin_path(path)

    # Register project specific plugins
    project_name = os.environ["AVALON_PROJECT"]
    project_plugins_paths = env.get("PYPE_PROJECT_PLUGINS") or ""
    for path in project_plugins_paths.split(os.pathsep):
        plugin_path = os.path.join(path, project_name, "plugins")
        if os.path.exists(plugin_path):
            pyblish.api.register_plugin_path(plugin_path)

    return publish.show()


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
