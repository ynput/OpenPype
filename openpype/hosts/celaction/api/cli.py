import os
import sys
import copy
import argparse

import pyblish.api
import pyblish.util

from openpype.api import Logger
import openpype
import openpype.hosts.celaction
from openpype.hosts.celaction import api as celaction
from openpype.tools.utils import host_tools
from openpype.pipeline.process_context import install_openpype_plugins


log = Logger().get_logger("Celaction_cli_publisher")

publish_host = "celaction"

HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.celaction.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")


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

    env["AVALON_PROJECT"] = project_name
    env["AVALON_ASSET"] = asset_name
    env["AVALON_TASK"] = os.getenv("AVALON_TASK")
    env["AVALON_WORKDIR"] = os.getenv("AVALON_WORKDIR")
    env["AVALON_APP"] = f"hosts.{publish_host}"
    env["AVALON_APP_NAME"] = "celaction/local"

    env["PYBLISH_HOSTS"] = publish_host

    os.environ.update(env)


def main():
    # prepare all environments
    _prepare_publish_environments()

    # Registers pype's Global pyblish plugins
    install_openpype_plugins()

    if os.path.exists(PUBLISH_PATH):
        log.info(f"Registering path: {PUBLISH_PATH}")
        pyblish.api.register_plugin_path(PUBLISH_PATH)

    pyblish.api.register_host(publish_host)

    return host_tools.show_publish()


if __name__ == "__main__":
    cli()
    result = main()
    sys.exit(not bool(result))
