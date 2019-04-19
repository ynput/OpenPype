import os
import sys
import json
import tempfile
import random
import string

from avalon import io
from avalon import api as avalon

import pype
from pypeapp import execute

import pyblish.api


pype.install()
PUBLISH_PATH = os.path.sep.join(
    [pype.PLUGINS_DIR, 'standalonepublish', 'publish']
)
pyblish.api.register_plugin_path(PUBLISH_PATH)


def set_context(project, asset, app):
    os.environ["AVALON_PROJECT"] = project
    io.Session["AVALON_PROJECT"] = project
    os.environ["AVALON_ASSET"] = asset
    io.Session["AVALON_ASSET"] = asset

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

    os.environ["AVALON_HIEARCHY"] = hierarchy
    io.Session["AVALON_HIEARCHY"] = hierarchy

    os.environ["AVALON_PROJECTCODE"] = av_project['data'].get('code', '')
    io.Session["AVALON_PROJECTCODE"] = av_project['data'].get('code', '')

    io.Session["current_dir"] = os.path.normpath(os.getcwd())

    os.environ["AVALON_APP"] = app
    io.Session["AVALON_APP"] = app

    io.uninstall()


def publish(data, gui=True):
    io.install()

    # Create hash name folder in temp
    chars = "".join( [random.choice(string.ascii_letters) for i in range(15)] )
    staging_dir = tempfile.mkdtemp(chars)#.replace("\\", "/")

    # create also json and fill with data
    json_data_path = staging_dir + os.path.basename(staging_dir) + '.json'
    with open(json_data_path, 'w') as outfile:
        json.dump(data, outfile)

    args = [
        "-pp", os.pathsep.join(pyblish.api.registered_paths())
    ]

    if gui:
        args += ["gui"]

    os.environ["PYBLISH_HOSTS"] = "shell"
    os.environ["ASAPUBLISH_INPATH"] = json_data_path

    returncode = execute([
        sys.executable, "-u", "-m", "pyblish"
    ] + args, env=os.environ)

    io.uninstall()
