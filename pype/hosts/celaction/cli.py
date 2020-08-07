import os
import sys
import copy
import argparse

from avalon import io
from avalon.tools import publish

import pyblish.api
import pyblish.util

from pype.api import Logger
import pype
from pype.hosts import celaction

log = Logger().get_logger("Celaction_cli_publisher")

publish_host = "celaction"

PUBLISH_PATH = os.path.join(pype.PLUGINS_DIR, publish_host, "publish")

PUBLISH_PATHS = [
    PUBLISH_PATH,
    os.path.join(pype.PLUGINS_DIR, "ftrack", "publish")
]


def cli():
    parser = argparse.ArgumentParser(prog="celaction_publish")

    parser.add_argument("--currentFile",
                        help="Pass file to Context as `currentFile`")

    parser.add_argument("--chunk",
                        help=("Render chanks on farm"))

    parser.add_argument("--frameStart",
                        help=("Start of frame range"))

    parser.add_argument("--frameEnd",
                        help=("End of frame range"))

    parser.add_argument("--resolutionWidth",
                        help=("Width of resolution"))

    parser.add_argument("--resolutionHeight",
                        help=("Height of resolution"))

    celaction.kwargs = parser.parse_args(sys.argv[1:]).__dict__


def _prepare_publish_environments():
    """Prepares environments based on request data."""
    env = copy.deepcopy(os.environ)

    project_name = os.getenv("AVALON_PROJECT")
    asset_name = os.getenv("AVALON_ASSET")

    io.install()
    project_doc = io.find_one({
        "type": "project"
    })
    av_asset = io.find_one({
        "type": "asset",
        "name": asset_name
    })
    parents = av_asset["data"]["parents"]
    hierarchy = ""
    if parents:
        hierarchy = "/".join(parents)

    env["AVALON_PROJECT"] = project_name
    env["AVALON_ASSET"] = asset_name
    env["AVALON_TASK"] = os.getenv("AVALON_TASK")
    env["AVALON_WORKDIR"] = os.getenv("AVALON_WORKDIR")
    env["AVALON_HIERARCHY"] = hierarchy
    env["AVALON_PROJECTCODE"] = project_doc["data"].get("code", "")
    env["AVALON_APP"] = f"hosts.{publish_host}"
    env["AVALON_APP_NAME"] = "celaction_local"

    env["PYBLISH_HOSTS"] = publish_host

    os.environ.update(env)


def main():
    # prepare all environments
    _prepare_publish_environments()

    # Registers pype's Global pyblish plugins
    pype.install()

    for path in PUBLISH_PATHS:
        path = os.path.normpath(path)

        if not os.path.exists(path):
            continue

        log.info(f"Registering path: {path}")
        pyblish.api.register_plugin_path(path)

    pyblish.api.register_host(publish_host)

    # Register project specific plugins
    project_name = os.environ["AVALON_PROJECT"]
    project_plugins_paths = os.getenv("PYPE_PROJECT_PLUGINS", "")
    for path in project_plugins_paths.split(os.pathsep):
        plugin_path = os.path.join(path, project_name, "plugins")
        if os.path.exists(plugin_path):
            pyblish.api.register_plugin_path(plugin_path)

    return publish.show()


if __name__ == "__main__":
    cli()
    result = main()
    sys.exit(not bool(result))
