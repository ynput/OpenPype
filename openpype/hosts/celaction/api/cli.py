import os
import sys
import argparse

import pyblish.api
import pyblish.util

import openpype.hosts.celaction
from openpype.lib import Logger
from openpype.hosts.celaction import api as celaction
from openpype.tools.utils import host_tools
from openpype.pipeline import install_openpype_plugins


log = Logger.get_logger("celaction")

PUBLISH_HOST = "celaction"
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


def main():
    # Registers pype's Global pyblish plugins
    install_openpype_plugins()

    if os.path.exists(PUBLISH_PATH):
        log.info(f"Registering path: {PUBLISH_PATH}")
        pyblish.api.register_plugin_path(PUBLISH_PATH)

    pyblish.api.register_host(PUBLISH_HOST)
    pyblish.api.register_target("local")

    return host_tools.show_publish()


if __name__ == "__main__":
    cli()
    result = main()
    sys.exit(not bool(result))
