# -*- coding: utf-8 -*-
"""Implementation of Pype commands."""
import os
import sys
import json
import time
import signal


class PypeCommands:
    """Class implementing commands used by Pype.

    Most of its methods are called by :mod:`cli` module.
    """
    @staticmethod
    def launch_tray():
        from openpype.lib import Logger
        from openpype.tools import tray

        Logger.set_process_name("Tray")

        tray.main()

    @staticmethod
    def launch_settings_gui(dev):
        from openpype.tools import settings

        # TODO change argument options to allow enum of user roles
        if dev:
            user_role = "developer"
        else:
            user_role = "manager"
        settings.main(user_role)

    @staticmethod
    def add_modules(click_func):
        """Modules/Addons can add their cli commands dynamically."""

        from openpype.lib import Logger
        from openpype.modules import ModulesManager

        manager = ModulesManager()
        log = Logger.get_logger("CLI-AddModules")
        for module in manager.modules:
            try:
                module.cli(click_func)

            except Exception:
                log.warning(
                    "Failed to add cli command for module \"{}\"".format(
                        module.name
                    )
                )
        return click_func

    @staticmethod
    def launch_eventservercli(*args):
        from openpype_modules.ftrack.ftrack_server.event_server_cli import (
            run_event_server
        )
        return run_event_server(*args)

    @staticmethod
    def launch_webpublisher_webservercli(*args, **kwargs):
        from openpype.hosts.webpublisher.webserver_service import run_webserver

        return run_webserver(*args, **kwargs)

    @staticmethod
    def launch_traypublisher():
        from openpype.tools import traypublisher
        traypublisher.main()

    @staticmethod
    def publish(paths, targets=None, gui=False):
        """Start headless publishing.

        Publish use json from passed paths argument.

        Args:
            paths (list): Paths to jsons.
            targets (string): What module should be targeted
                (to choose validator for example)
            gui (bool): Show publish UI.

        Raises:
            RuntimeError: When there is no path to process.
        """

        from openpype.lib import Logger
        from openpype.lib.applications import (
            get_app_environments_for_context,
            LaunchTypes,
        )
        from openpype.modules import ModulesManager
        from openpype.pipeline import (
            install_openpype_plugins,
            get_global_context,
        )
        from openpype.tools.utils.host_tools import show_publish
        from openpype.tools.utils.lib import qt_app_context

        # Register target and host
        import pyblish.api
        import pyblish.util

        log = Logger.get_logger("CLI-publish")

        install_openpype_plugins()

        manager = ModulesManager()

        publish_paths = manager.collect_plugin_paths()["publish"]

        for path in publish_paths:
            pyblish.api.register_plugin_path(path)

        if not any(paths):
            raise RuntimeError("No publish paths specified")

        app_full_name = os.getenv("AVALON_APP_NAME")
        if app_full_name:
            context = get_global_context()
            env = get_app_environments_for_context(
                context["project_name"],
                context["asset_name"],
                context["task_name"],
                app_full_name,
                launch_type=LaunchTypes.farm_publish,
            )
            os.environ.update(env)

        pyblish.api.register_host("shell")

        if targets:
            for target in targets:
                print(f"setting target: {target}")
                pyblish.api.register_target(target)
        else:
            pyblish.api.register_target("farm")

        os.environ["OPENPYPE_PUBLISH_DATA"] = os.pathsep.join(paths)
        os.environ["HEADLESS_PUBLISH"] = 'true'  # to use in app lib

        log.info("Running publish ...")

        plugins = pyblish.api.discover()
        print("Using plugins:")
        for plugin in plugins:
            print(plugin)

        if gui:
            with qt_app_context():
                show_publish()
        else:
            # Error exit as soon as any error occurs.
            error_format = ("Failed {plugin.__name__}: "
                            "{error} -- {error.traceback}")

            for result in pyblish.util.publish_iter():
                if result["error"]:
                    log.error(error_format.format(**result))
                    # uninstall()
                    sys.exit(1)

        log.info("Publish finished.")

    @staticmethod
    def extractenvironments(output_json_path, project, asset, task, app,
                            env_group):
        """Produces json file with environment based on project and app.

        Called by Deadline plugin to propagate environment into render jobs.
        """

        from openpype.lib.applications import (
            get_app_environments_for_context,
            LaunchTypes,
        )

        if all((project, asset, task, app)):
            env = get_app_environments_for_context(
                project,
                asset,
                task,
                app,
                env_group=env_group,
                launch_type=LaunchTypes.farm_render
            )
        else:
            env = os.environ.copy()

        output_dir = os.path.dirname(output_json_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(output_json_path, "w") as file_stream:
            json.dump(env, file_stream, indent=4)

    @staticmethod
    def launch_project_manager():
        from openpype.tools import project_manager

        project_manager.main()

    @staticmethod
    def contextselection(output_path, project_name, asset_name, strict):
        from openpype.tools.context_dialog import main

        main(output_path, project_name, asset_name, strict)

    def validate_jsons(self):
        pass

    def run_tests(self, folder, mark, pyargs,
                  test_data_folder, persist, app_variant, timeout, setup_only,
                  mongo_url, app_group, dump_databases):
        """
            Runs tests from 'folder'

            Args:
                 folder (str): relative path to folder with tests
                 mark (str): label to run tests marked by it (slow etc)
                 pyargs (str): package path to test
                 test_data_folder (str): url to unzipped folder of test data
                 persist (bool): True if keep test db and published after test
                    end
                app_variant (str): variant (eg 2020 for AE), empty if use
                    latest installed version
                timeout (int): explicit timeout for single test
                setup_only (bool): if only preparation steps should be
                    triggered, no tests (useful for debugging/development)
                mongo_url (str): url to Openpype Mongo database
        """
        print("run_tests")
        if folder:
            folder = " ".join(list(folder))
        else:
            folder = "../tests"

        # disable warnings and show captured stdout even if success
        args = [
            "--disable-pytest-warnings",
            "--capture=sys",
            "--print",
            "-W ignore::DeprecationWarning",
            "-rP",
            folder
        ]

        if mark:
            args.extend(["-m", mark])

        if pyargs:
            args.extend(["--pyargs", pyargs])

        if test_data_folder:
            args.extend(["--test_data_folder", test_data_folder])

        if persist:
            args.extend(["--persist", persist])

        if app_group:
            args.extend(["--app_group", app_group])

        if app_variant:
            args.extend(["--app_variant", app_variant])

        if timeout:
            args.extend(["--timeout", timeout])

        if setup_only:
            args.extend(["--setup_only", setup_only])

        if mongo_url:
            args.extend(["--mongo_url", mongo_url])

        if dump_databases:
            msg = "dump_databases format is not recognized: {}".format(
                dump_databases
            )
            assert dump_databases in ["bson", "json"], msg
            args.extend(["--dump_databases", dump_databases])

        print("run_tests args: {}".format(args))
        import pytest
        pytest.main(args)

    def repack_version(self, directory):
        """Repacking OpenPype version."""
        from openpype.tools.repack_version import VersionRepacker

        version_packer = VersionRepacker(directory)
        version_packer.process()

    def pack_project(self, project_name, dirpath, database_only):
        from openpype.lib.project_backpack import pack_project

        if database_only and not dirpath:
            raise ValueError((
                "Destination dir must be defined when using --dbonly."
                " Use '--dirpath {output dir path}' flag"
                " to specify directory."
            ))

        pack_project(project_name, dirpath, database_only)

    def unpack_project(self, zip_filepath, new_root, database_only):
        from openpype.lib.project_backpack import unpack_project

        unpack_project(zip_filepath, new_root, database_only)
