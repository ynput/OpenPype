"""Launch scripts module."""
import os
import time

import click

from openpype.modules import OpenPypeModule

from .lib import find_app_variant
from .run_script import (
    run_script as _run_script
)


class LaunchScriptsModule(OpenPypeModule):
    label = "Publish Workfile"
    name = "launch_scripts"

    def initialize(self, modules_settings):
        self.enabled = True

    def cli(self, click_group):
        click_group.add_command(cli_main)


@click.group(LaunchScriptsModule.name,
             help="Publish Workfile cli commands.")
def cli_main():
    pass


@cli_main.command()
@click.option("-project", "--project_name",
              required=True,
              envvar="AVALON_PROJECT",
              help="Project name")
@click.option("-asset", "--asset_name",
              required=True,
              envvar="AVALON_ASSET",
              help="Asset name")
@click.option("-task", "--task_name",
              required=True,
              envvar="AVALON_TASK",
              help="Task name")
@click.option("-path", "--filepath",
              required=True,
              help="Absolute filepath to workfile to publish")
@click.option("-app", "--app_name",
              envvar="AVALON_APP",
              required=True,
              help="App name, specific variant 'maya/2023' or just 'maya' to "
                   "take latest found variant for which current machine has "
                   "an existing executable.")
def run_script(project_name,
               asset_name,
               task_name,
               filepath,
               app_name,
               timeout=None):
    app_name = find_app_variant(app_name)
    launched_app = _run_script(
        project_name=project_name,
        asset_name=asset_name,
        task_name=task_name,
        app_name=app_name,
        script_path=filepath
    )
    _print_stdout_until_timeout(launched_app, timeout, app_name)

    print("Application shut down.")


@cli_main.command()
@click.option("-project", "--project_name",
              required=True,
              envvar="AVALON_PROJECT",
              help="Project name")
@click.option("-asset", "--asset_name",
              required=True,
              envvar="AVALON_ASSET",
              help="Asset name")
@click.option("-task", "--task_name",
              required=True,
              envvar="AVALON_TASK",
              help="Task name")
@click.option("-path", "--filepath",
              required=True,
              help="Absolute filepath to workfile to publish")
@click.option("-app", "--app_name",
              envvar="AVALON_APP_NAME",
              required=True,
              help="App name, specific variant 'maya/2023' or just 'maya' to "
                   "take latest found variant for which current machine has "
                   "an existing executable.")
@click.option("-pre", "--pre_publish_script",
              multiple=True,
              help="Pre process script path")
@click.option("-post", "--post_publish_script",
              multiple=True,
              help="Post process script path")
@click.option("-c", "--comment",
              help="Publish comment")
def publish(project_name,
            asset_name,
            task_name,
            filepath,
            app_name=None,
            pre_publish_script=None,
            post_publish_script=None,
            comment=None,
            timeout=None):
    """Publish a workfile standalone for a host."""

    # The entry point should be a script that opens the workfile since the
    # `run_script` interface doesn't have an "open with file" argument due to
    # some hosts triggering scripts before opening the file or not allowing
    # both scripts to run and a file to open. As such, the best entry point
    # is to just open in the host instead and allow the script itself to open
    # a file.

    print(f"Using context {project_name} > {asset_name} > {task_name}")
    print(f"Publishing workfile: {filepath}")

    if not os.path.exists(filepath):
        raise RuntimeError(f"Filepath does not exist: {filepath}")

    # Pass specific arguments to the publish script using environment variables
    env = os.environ.copy()
    env["PUBLISH_WORKFILE"] = filepath

    if pre_publish_script:
        print(f"Pre scripts: {', '.join(pre_publish_script)}")
        env["PUBLISH_PRE_SCRIPTS"] = os.pathsep.join(pre_publish_script)
    if post_publish_script:
        print(f"Post scripts: {', '.join(post_publish_script)}")
        env["PUBLISH_PRE_SCRIPTS"] = os.pathsep.join(post_publish_script)
    if comment:
        env["PUBLISH_COMMENT"] = comment

    script_path = os.path.join(os.path.dirname(__file__),
                               "scripts",
                               "publish_script.py")

    app_name = find_app_variant(app_name)
    launched_app = _run_script(
        project_name=project_name,
        asset_name=asset_name,
        task_name=task_name,
        app_name=app_name,
        script_path=script_path,
        env=env
    )
    _print_stdout_until_timeout(launched_app, timeout, app_name)

    print("Application shut down.")


def _print_stdout_until_timeout(popen,
                                timeout=None,
                                app_name=None):
    """Print stdout until app close.

    If app remains open for longer than `timeout` then app is terminated.

    """
    time_start = time.time()
    prefix = f"{app_name}: " if app_name else " "
    for line in popen.stdout:
        # Print stdout
        line_str = line.decode("utf-8")
        print(f"{prefix}{line_str}", end='')

        if timeout and time.time() - time_start > timeout:
            popen.terminate()
            raise RuntimeError("Timeout reached")
