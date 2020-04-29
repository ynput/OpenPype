import sys
import argparse
import os
import copy
from avalon import io
from pypeapp import execute, Logger

log = Logger().get_logger("Celaction_cli_publisher")

publish_host = "celaction"

CURRENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(CURRENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, publish_host, "publish")
PUBLISH_SCRIPT_PATH = os.path.join(CURRENT_DIR, "publish.py")

PUBLISH_PATHS = [
    PUBLISH_PATH,
    os.path.join(PLUGINS_DIR, "ftrack", "publish")
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

    parser.add_argument("--programDir",
                        help=("Directory with celaction program installation"))

    return parser.parse_args(sys.argv[1:]).__dict__


def publish(data):
    """Triggers publishing script in subprocess.

    """
    try:
        publish_env = _prepare_publish_environments(
            data
        )
    except Exception as exc:
        log.warning(
            "Failed to prepare environments for publishing.",
            exc_info=True
        )
        Exception(str(exc))

    log.info("Pyblish is running")
    try:
        # Trigger subprocess
        # QUESTION should we check returncode?
        returncode = execute(
            [sys.executable, PUBLISH_SCRIPT_PATH],
            env=publish_env
        )

        # Check if output file exists
        if returncode != 0:
            Exception("Publishing failed")

        log.info("Pyblish have stopped")

        return True

    except Exception:
        log.warning("Publishing failed", exc_info=True)
        Exception("Publishing failed")


def _prepare_publish_environments(data):
    """Prepares environments based on request data."""
    env = copy.deepcopy(os.environ)

    project_name = data["project"]
    asset_name = data["asset"]

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
    env["AVALON_TASK"] = data["task"]
    env["AVALON_WORKDIR"] = data["workdir"]
    env["AVALON_HIERARCHY"] = hierarchy
    env["AVALON_PROJECTCODE"] = project_doc["data"].get("code", "")
    env["AVALON_APP"] = publish_host
    env["AVALON_APP_NAME"] = publish_host

    env["PYBLISH_HOSTS"] = publish_host
    env["PUBLISH_PATHS"] = os.pathsep.join(PUBLISH_PATHS)
    return env


if __name__ == "__main__":
    data = cli()
    publish(data)
