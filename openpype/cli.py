# -*- coding: utf-8 -*-
"""Package for handling pype command line arguments."""
import os
import sys
import code
import click

from openpype import AYON_SERVER_ENABLED
from .pype_commands import PypeCommands


class AliasedGroup(click.Group):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aliases = {}

    def set_alias(self, src_name, dst_name):
        self._aliases[dst_name] = src_name

    def get_command(self, ctx, cmd_name):
        if cmd_name in self._aliases:
            cmd_name = self._aliases[cmd_name]
        return super().get_command(ctx, cmd_name)


@click.group(cls=AliasedGroup, invoke_without_command=True)
@click.pass_context
@click.option("--use-version",
              expose_value=False, help="use specified version")
@click.option("--use-staging", is_flag=True,
              expose_value=False, help="use staging variants")
@click.option("--list-versions", is_flag=True, expose_value=False,
              help="list all detected versions.")
@click.option("--validate-version", expose_value=False,
              help="validate given version integrity")
@click.option("--debug", is_flag=True, expose_value=False,
              help="Enable debug")
@click.option("--verbose", expose_value=False,
              help=("Change OpenPype log level (debug - critical or 0-50)"))
@click.option("--automatic-tests", is_flag=True, expose_value=False,
              help=("Run in automatic tests mode"))
def main(ctx):
    """Pype is main command serving as entry point to pipeline system.

    It wraps different commands together.
    """

    if ctx.invoked_subcommand is None:
        # Print help if headless mode is used
        if AYON_SERVER_ENABLED:
            is_headless = os.getenv("AYON_HEADLESS_MODE") == "1"
        else:
            is_headless = os.getenv("OPENPYPE_HEADLESS_MODE") == "1"
        if is_headless:
            print(ctx.get_help())
            sys.exit(0)
        else:
            ctx.invoke(tray)


@main.command()
@click.option("-d", "--dev", is_flag=True, help="Settings in Dev mode")
def settings(dev):
    """Show Pype Settings UI."""

    if AYON_SERVER_ENABLED:
        raise RuntimeError("AYON does not support 'settings' command.")
    PypeCommands().launch_settings_gui(dev)


@main.command()
def tray():
    """Launch pype tray.

    Default action of pype command is to launch tray widget to control basic
    aspects of pype. See documentation for more information.
    """
    PypeCommands().launch_tray()


@PypeCommands.add_modules
@main.group(help="Run command line arguments of OpenPype addons")
@click.pass_context
def module(ctx):
    """Addon specific commands created dynamically.

    These commands are generated dynamically by currently loaded addons.
    """
    pass


# Add 'addon' as alias for module
main.set_alias("module", "addon")


@main.command()
@click.option("--ftrack-url", envvar="FTRACK_SERVER",
              help="Ftrack server url")
@click.option("--ftrack-user", envvar="FTRACK_API_USER",
              help="Ftrack api user")
@click.option("--ftrack-api-key", envvar="FTRACK_API_KEY",
              help="Ftrack api key")
@click.option("--legacy", is_flag=True,
              help="run event server without mongo storing")
@click.option("--clockify-api-key", envvar="CLOCKIFY_API_KEY",
              help="Clockify API key.")
@click.option("--clockify-workspace", envvar="CLOCKIFY_WORKSPACE",
              help="Clockify workspace")
def eventserver(ftrack_url,
                ftrack_user,
                ftrack_api_key,
                legacy,
                clockify_api_key,
                clockify_workspace):
    """Launch ftrack event server.

    This should be ideally used by system service (such us systemd or upstart
    on linux and window service).
    """

    if AYON_SERVER_ENABLED:
        raise RuntimeError("AYON does not support 'eventserver' command.")
    PypeCommands().launch_eventservercli(
        ftrack_url,
        ftrack_user,
        ftrack_api_key,
        legacy,
        clockify_api_key,
        clockify_workspace
    )


@main.command()
@click.option("-h", "--host", help="Host", default=None)
@click.option("-p", "--port", help="Port", default=None)
@click.option("-e", "--executable", help="Executable")
@click.option("-u", "--upload_dir", help="Upload dir")
def webpublisherwebserver(executable, upload_dir, host=None, port=None):
    """Starts webserver for communication with Webpublish FR via command line

        OP must be congigured on a machine, eg. OPENPYPE_MONGO filled AND
        FTRACK_BOT_API_KEY provided with api key from Ftrack.

        Expect "pype.club" user created on Ftrack.
    """

    if AYON_SERVER_ENABLED:
        raise RuntimeError(
            "AYON does not support 'webpublisherwebserver' command."
        )
    PypeCommands().launch_webpublisher_webservercli(
        upload_dir=upload_dir,
        executable=executable,
        host=host,
        port=port
    )


@main.command()
@click.argument("output_json_path")
@click.option("--project", help="Project name", default=None)
@click.option("--asset", help="Asset name", default=None)
@click.option("--task", help="Task name", default=None)
@click.option("--app", help="Application name", default=None)
@click.option(
    "--envgroup", help="Environment group (e.g. \"farm\")", default=None
)
def extractenvironments(output_json_path, project, asset, task, app, envgroup):
    """Extract environment variables for entered context to a json file.

    Entered output filepath will be created if does not exists.

    All context options must be passed otherwise only pype's global
    environments will be extracted.

    Context options are "project", "asset", "task", "app"
    """
    PypeCommands.extractenvironments(
        output_json_path, project, asset, task, app, envgroup
    )


@main.command()
@click.argument("paths", nargs=-1)
@click.option("-t", "--targets", help="Targets module", default=None,
              multiple=True)
@click.option("-g", "--gui", is_flag=True,
              help="Show Publish UI", default=False)
def publish(paths, targets, gui):
    """Start CLI publishing.

    Publish collects json from paths provided as an argument.
    More than one path is allowed.
    """

    PypeCommands.publish(list(paths), targets, gui)


@main.command(context_settings={"ignore_unknown_options": True})
def projectmanager():
    if AYON_SERVER_ENABLED:
        raise RuntimeError("AYON does not support 'projectmanager' command.")
    PypeCommands().launch_project_manager()


@main.command(context_settings={"ignore_unknown_options": True})
def publish_report_viewer():
    from openpype.tools.publisher.publish_report_viewer import main

    sys.exit(main())


@main.command()
@click.argument("output_path")
@click.option("--project", help="Define project context")
@click.option("--asset", help="Define asset in project (project must be set)")
@click.option(
    "--strict",
    is_flag=True,
    help="Full context must be set otherwise dialog can't be closed."
)
def contextselection(
    output_path,
    project,
    asset,
    strict
):
    """Show Qt dialog to select context.

    Context is project name, asset name and task name. The result is stored
    into json file which path is passed in first argument.
    """
    PypeCommands.contextselection(
        output_path,
        project,
        asset,
        strict
    )


@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True))
@click.argument("script", required=True, type=click.Path(exists=True))
def run(script):
    """Run python script in Pype context."""
    import runpy

    if not script:
        print("Error: missing path to script file.")
    else:

        args = sys.argv
        args.remove("run")
        args.remove(script)
        sys.argv = args
        args_string = " ".join(args[1:])
        print(f"... running: {script} {args_string}")
        runpy.run_path(script, run_name="__main__", )


@main.command()
@click.argument("folder", nargs=-1)
@click.option("-m",
              "--mark",
              help="Run tests marked by",
              default=None)
@click.option("-p",
              "--pyargs",
              help="Run tests from package",
              default=None)
@click.option("-t",
              "--test_data_folder",
              help="Unzipped directory path of test file",
              default=None)
@click.option("-s",
              "--persist",
              help="Persist test DB and published files after test end",
              default=None)
@click.option("-a",
              "--app_variant",
              help="Provide specific app variant for test, empty for latest",
              default=None)
@click.option("-t",
              "--timeout",
              help="Provide specific timeout value for test case",
              default=None)
@click.option("-so",
              "--setup_only",
              help="Only create dbs, do not run tests",
              default=None)
@click.option("--mongo_url",
              help="MongoDB for testing.",
              default=None)
def runtests(folder, mark, pyargs, test_data_folder, persist, app_variant,
             timeout, setup_only, mongo_url):
    """Run all automatic tests after proper initialization via start.py"""
    PypeCommands().run_tests(folder, mark, pyargs, test_data_folder,
                             persist, app_variant, timeout, setup_only,
                             mongo_url)


@main.command(help="DEPRECATED - run sync server")
@click.pass_context
@click.option("-a", "--active_site", required=True,
              help="Name of active site")
def syncserver(ctx, active_site):
    """Run sync site server in background.

    Deprecated:
        This command is deprecated and will be removed in future versions.
        Use '~/openpype_console module sync_server syncservice' instead.

    Details:
        Some Site Sync use cases need to expose site to another one.
        For example if majority of artists work in studio, they are not using
        SS at all, but if you want to expose published assets to 'studio' site
        to SFTP for only a couple of artists, some background process must
        mark published assets to live on multiple sites (they might be
        physically in same location - mounted shared disk).

        Process mimics OP Tray with specific 'active_site' name, all
        configuration for this "dummy" user comes from Setting or Local
        Settings (configured by starting OP Tray with env
        var OPENPYPE_LOCAL_ID set to 'active_site'.
    """

    if AYON_SERVER_ENABLED:
        raise RuntimeError("AYON does not support 'syncserver' command.")

    from openpype.modules.sync_server.sync_server_module import (
        syncservice)
    ctx.invoke(syncservice, active_site=active_site)


@main.command()
@click.argument("directory")
def repack_version(directory):
    """Repack OpenPype version from directory.

    This command will re-create zip file from specified directory,
    recalculating file checksums. It will try to use version detected in
    directory name.
    """
    if AYON_SERVER_ENABLED:
        raise RuntimeError("AYON does not support 'repack-version' command.")
    PypeCommands().repack_version(directory)


@main.command()
@click.option("--project", help="Project name")
@click.option(
    "--dirpath", help="Directory where package is stored", default=None)
@click.option(
    "--dbonly", help="Store only Database data", default=False, is_flag=True)
def pack_project(project, dirpath, dbonly):
    """Create a package of project with all files and database dump."""

    if AYON_SERVER_ENABLED:
        raise RuntimeError("AYON does not support 'pack-project' command.")
    PypeCommands().pack_project(project, dirpath, dbonly)


@main.command()
@click.option("--zipfile", help="Path to zip file")
@click.option(
    "--root", help="Replace root which was stored in project", default=None
)
@click.option(
    "--dbonly", help="Store only Database data", default=False, is_flag=True)
def unpack_project(zipfile, root, dbonly):
    """Create a package of project with all files and database dump."""
    if AYON_SERVER_ENABLED:
        raise RuntimeError("AYON does not support 'unpack-project' command.")
    PypeCommands().unpack_project(zipfile, root, dbonly)


@main.command()
def interactive():
    """Interactive (Python like) console.

    Helpful command not only for development to directly work with python
    interpreter.

    Warning:
        Executable 'openpype_gui' on Windows won't work.
    """

    if AYON_SERVER_ENABLED:
        version = os.environ["AYON_VERSION"]
        banner = (
            f"AYON launcher {version}\nPython {sys.version} on {sys.platform}"
        )
    else:
        from openpype.version import __version__

        banner = (
            f"OpenPype {__version__}\nPython {sys.version} on {sys.platform}"
        )
    code.interact(banner)


@main.command()
@click.option("--build", help="Print only build version",
              is_flag=True, default=False)
def version(build):
    """Print OpenPype version."""
    if AYON_SERVER_ENABLED:
        print(os.environ["AYON_VERSION"])
        return

    from openpype.version import __version__
    from igniter.bootstrap_repos import BootstrapRepos, OpenPypeVersion
    from pathlib import Path

    if getattr(sys, 'frozen', False):
        local_version = BootstrapRepos.get_version(
            Path(os.getenv("OPENPYPE_ROOT")))
    else:
        local_version = OpenPypeVersion.get_installed_version_str()

    if build:
        print(local_version)
        return
    print(f"{__version__} (booted: {local_version})")
