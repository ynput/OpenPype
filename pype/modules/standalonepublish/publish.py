import os
import sys
import json
import tempfile
import random
import string

from avalon import io, api
from avalon.tools import publish as av_publish

import pype
from pype.api import execute

import pyblish.api
from . import PUBLISH_PATHS


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
    # # this uses avalon pyblish launch tool
    # avalon_api_publish(data, gui)


def avalon_api_publish(data, gui=True):
    ''' Launches Pyblish (GUI by default)
    :param data: Should include data for pyblish and standalone collector
    :type data: dict
    :param gui: Pyblish will be launched in GUI mode if set to True
    :type gui: bool
    '''
    io.install()

    # Create hash name folder in temp
    chars = "".join([random.choice(string.ascii_letters) for i in range(15)])
    staging_dir = tempfile.mkdtemp(chars)

    # create also json and fill with data
    json_data_path = staging_dir + os.path.basename(staging_dir) + '.json'
    with open(json_data_path, 'w') as outfile:
        json.dump(data, outfile)

    args = [
        "-pp", os.pathsep.join(pyblish.api.registered_paths())
    ]

    envcopy = os.environ.copy()
    envcopy["PYBLISH_HOSTS"] = "standalonepublisher"
    envcopy["SAPUBLISH_INPATH"] = json_data_path

    if gui:
        av_publish.show()
    else:
        returncode = execute([
            sys.executable, "-u", "-m", "pyblish"
        ] + args, env=envcopy)

    io.uninstall()


def cli_publish(data, gui=True):
    io.install()

    pyblish.api.deregister_all_plugins()
    # Registers Global pyblish plugins
    pype.install()
    # Registers Standalone pyblish plugins
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

    # Create hash name folder in temp
    chars = "".join([random.choice(string.ascii_letters) for i in range(15)])
    staging_dir = tempfile.mkdtemp(chars)

    # create json for return data
    return_data_path = (
        staging_dir + os.path.basename(staging_dir) + 'return.json'
    )
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
    envcopy["PYBLISH_HOSTS"] = "standalonepublisher"
    envcopy["SAPUBLISH_INPATH"] = json_data_path
    envcopy["SAPUBLISH_OUTPATH"] = return_data_path
    envcopy["PYBLISH_GUI"] = "pyblish_lite"

    returncode = execute([
        sys.executable, "-u", "-m", "pyblish"
    ] + args, env=envcopy)

    result = {}
    if os.path.exists(json_data_path):
        with open(json_data_path, "r") as f:
            result = json.load(f)

    io.uninstall()
    # TODO: check if was pyblish successful
    # if successful return True
    print('Check result here')
    return False
