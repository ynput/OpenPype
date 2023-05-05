import os
import json

import click

from openpype.modules import OpenPypeModule, ModulesManager

from .exceptions import ApplicationNotFound


class ApplicationsAddon(OpenPypeModule):
    name = "applications"

    def initialize(self, module_settings):
        self.enabled = True

    def create_applications_manager(self):
        from .manager import ApplicationManager

        return ApplicationManager()

    def launch_app(self, app_name, **kwargs):
        manager = self.create_applications_manager()
        app = manager.applications.get(app_name)
        if app is None:
            raise ApplicationNotFound(app_name)

        manager.launch(app_name, **kwargs)

    def get_app_launch_environments(
        self,
        app_name,
        project_name,
        asset_name,
        task_name,
        env_group=None
    ):
        from .utils import get_app_environments_for_context

        if all((project_name, asset_name, task_name, app_name)):
            return get_app_environments_for_context(
                project_name, asset_name, task_name, app_name, env_group
            )
        return os.environ.copy()

    def cli(self, click_group):
        click_group.add_command(cli_main)


@click.group(ApplicationsAddon.name, help="Applications addon commands.")
def cli_main():
    pass


@cli_main.command()
@click.argument("output_json_path")
@click.option("--project", help="Project name", default=None)
@click.option("--asset", help="Asset name", default=None)
@click.option("--task", help="Task name", default=None)
@click.option("--app", help="Application name", default=None)
@click.option(
    "--envgroup", help="Environment group (e.g. \"farm\")", default=None
)
def extractenvironments(
    output_json_path,
    project,
    asset,
    task,
    app,
    env_group
):
    """Produces json file with environment based on project and app.

    Called by Deadline plugin to propagate environment into render jobs.
    """

    manager = ModulesManager()
    addon = manager.get_enabled_module(ApplicationsAddon.name)
    env = addon.get_app_launch_environments(
        app, project, asset, task, env_group)


    output_dir = os.path.dirname(output_json_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_json_path, "w") as file_stream:
        json.dump(env, file_stream, indent=4)