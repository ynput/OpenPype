# -*- coding: utf-8 -*-
"""Implementation of Pype commands."""
import os
import sys
import json
import time

from openpype.lib import PypeLogger
from openpype.api import get_app_environments_for_context
from openpype.lib.plugin_tools import parse_json, get_batch_asset_task_info
from openpype.lib.remote_publish import (
    get_webpublish_conn,
    start_webpublish_log,
    publish_and_log,
    fail_batch,
    find_variant_key,
    get_task_data,
    IN_PROGRESS_STATUS
)


class PypeCommands:
    """Class implementing commands used by Pype.

    Most of its methods are called by :mod:`cli` module.
    """
    @staticmethod
    def launch_tray(debug=False):
        PypeLogger.set_process_name("Tray")

        from openpype.tools import tray

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
        from openpype.modules import ModulesManager

        manager = ModulesManager()
        log = PypeLogger.get_logger("AddModulesCLI")
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
        from openpype.hosts.webpublisher.webserver_service.webserver_cli \
            import (run_webserver)
        return run_webserver(*args, **kwargs)

    @staticmethod
    def launch_standalone_publisher():
        from openpype.tools import standalonepublish
        standalonepublish.main()

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
        from openpype.modules import ModulesManager
        from openpype.pipeline import install_openpype_plugins

        from openpype.api import Logger
        from openpype.tools.utils.host_tools import show_publish
        from openpype.tools.utils.lib import qt_app_context

        # Register target and host
        import pyblish.api
        import pyblish.util

        log = Logger.get_logger()

        install_openpype_plugins()

        manager = ModulesManager()

        publish_paths = manager.collect_plugin_paths()["publish"]

        for path in publish_paths:
            pyblish.api.register_plugin_path(path)

        if not any(paths):
            raise RuntimeError("No publish paths specified")

        env = get_app_environments_for_context(
            os.environ["AVALON_PROJECT"],
            os.environ["AVALON_ASSET"],
            os.environ["AVALON_TASK"],
            os.environ["AVALON_APP_NAME"]
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
    def remotepublishfromapp(project, batch_path, host_name,
                             user_email, targets=None):
        """Opens installed variant of 'host' and run remote publish there.

        Currently implemented and tested for Photoshop where customer
        wants to process uploaded .psd file and publish collected layers
        from there.

        Checks if no other batches are running (status =='in_progress). If
        so, it sleeps for SLEEP (this is separate process),
        waits for WAIT_FOR seconds altogether.

        Requires installed host application on the machine.

        Runs publish process as user would, in automatic fashion.

        Args:
            project (str): project to publish (only single context is expected
                per call of remotepublish
            batch_path (str): Path batch folder. Contains subfolders with
                resources (workfile, another subfolder 'renders' etc.)
            host_name (str): 'photoshop'
            user_email (string): email address for webpublisher - used to
                find Ftrack user with same email
            targets (list): Pyblish targets
                (to choose validator for example)
        """
        import pyblish.api
        from openpype.api import Logger
        from openpype.lib import ApplicationManager

        log = Logger.get_logger()

        log.info("remotepublishphotoshop command")

        task_data = get_task_data(batch_path)

        workfile_path = os.path.join(batch_path,
                                     task_data["task"],
                                     task_data["files"][0])

        print("workfile_path {}".format(workfile_path))

        batch_id = task_data["batch"]
        dbcon = get_webpublish_conn()
        # safer to start logging here, launch might be broken altogether
        _id = start_webpublish_log(dbcon, batch_id, user_email)

        batches_in_progress = list(dbcon.find({"status": IN_PROGRESS_STATUS}))
        if len(batches_in_progress) > 1:
            fail_batch(_id, batches_in_progress, dbcon)
            print("Another batch running, probably stuck, ask admin for help")

        asset, task_name, _ = get_batch_asset_task_info(task_data["context"])

        application_manager = ApplicationManager()
        found_variant_key = find_variant_key(application_manager, host_name)
        app_name = "{}/{}".format(host_name, found_variant_key)

        # must have for proper launch of app
        env = get_app_environments_for_context(
            project,
            asset,
            task_name,
            app_name
        )
        print("env:: {}".format(env))
        os.environ.update(env)

        os.environ["OPENPYPE_PUBLISH_DATA"] = batch_path
        # must pass identifier to update log lines for a batch
        os.environ["BATCH_LOG_ID"] = str(_id)
        os.environ["HEADLESS_PUBLISH"] = 'true'  # to use in app lib
        os.environ["USER_EMAIL"] = user_email

        pyblish.api.register_host(host_name)
        if targets:
            if isinstance(targets, str):
                targets = [targets]
            current_targets = os.environ.get("PYBLISH_TARGETS", "").split(
                os.pathsep)
            for target in targets:
                current_targets.append(target)

            os.environ["PYBLISH_TARGETS"] = os.pathsep.join(
                set(current_targets))

        data = {
            "last_workfile_path": workfile_path,
            "start_last_workfile": True,
            "project_name": project,
            "asset_name": asset,
            "task_name": task_name
        }

        launched_app = application_manager.launch(app_name, **data)

        while launched_app.poll() is None:
            time.sleep(0.5)

    @staticmethod
    def remotepublish(project, batch_path, user_email, targets=None):
        """Start headless publishing.

        Used to publish rendered assets, workfiles etc.

        Publish use json from passed paths argument.

        Args:
            project (str): project to publish (only single context is expected
                per call of remotepublish
            batch_path (str): Path batch folder. Contains subfolders with
                resources (workfile, another subfolder 'renders' etc.)
            user_email (string): email address for webpublisher - used to
                find Ftrack user with same email
            targets (list): Pyblish targets
                (to choose validator for example)

        Raises:
            RuntimeError: When there is no path to process.
        """
        if not batch_path:
            raise RuntimeError("No publish paths specified")

        # Register target and host
        import pyblish.api
        import pyblish.util

        from openpype.pipeline import install_host
        from openpype.hosts.webpublisher import api as webpublisher

        log = PypeLogger.get_logger()

        log.info("remotepublish command")

        host_name = "webpublisher"
        os.environ["OPENPYPE_PUBLISH_DATA"] = batch_path
        os.environ["AVALON_PROJECT"] = project
        os.environ["AVALON_APP"] = host_name
        os.environ["USER_EMAIL"] = user_email

        pyblish.api.register_host(host_name)

        if targets:
            if isinstance(targets, str):
                targets = [targets]
            for target in targets:
                pyblish.api.register_target(target)

        install_host(webpublisher)

        log.info("Running publish ...")

        _, batch_id = os.path.split(batch_path)
        dbcon = get_webpublish_conn()
        _id = start_webpublish_log(dbcon, batch_id, user_email)

        publish_and_log(dbcon, _id, log, batch_id=batch_id)

        log.info("Publish finished.")

    @staticmethod
    def extractenvironments(
        output_json_path, project, asset, task, app, env_group
    ):
        if all((project, asset, task, app)):
            from openpype.api import get_app_environments_for_context
            env = get_app_environments_for_context(
                project, asset, task, app, env_group
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

    def texture_copy(self, project, asset, path):
        pass

    def run_application(self, app, project, asset, task, tools, arguments):
        pass

    def validate_jsons(self):
        pass

    def run_tests(self, folder, mark, pyargs,
                  test_data_folder, persist, app_variant, timeout):
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
        """
        print("run_tests")
        if folder:
            folder = " ".join(list(folder))
        else:
            folder = "../tests"

        # disable warnings and show captured stdout even if success
        args = ["--disable-pytest-warnings", "-rP", folder]

        if mark:
            args.extend(["-m", mark])

        if pyargs:
            args.extend(["--pyargs", pyargs])

        if persist:
            args.extend(["--test_data_folder", test_data_folder])

        if persist:
            args.extend(["--persist", persist])

        if app_variant:
            args.extend(["--app_variant", app_variant])

        if timeout:
            args.extend(["--timeout", timeout])

        print("run_tests args: {}".format(args))
        import pytest
        pytest.main(args)

    def syncserver(self, active_site):
        """Start running sync_server in background."""
        import signal
        os.environ["OPENPYPE_LOCAL_ID"] = active_site

        def signal_handler(sig, frame):
            print("You pressed Ctrl+C. Process ended.")
            sync_server_module.server_exit()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        from openpype.modules import ModulesManager

        manager = ModulesManager()
        sync_server_module = manager.modules_by_name["sync_server"]

        sync_server_module.server_init()
        sync_server_module.server_start()

        import time
        while True:
            time.sleep(1.0)

    def repack_version(self, directory):
        """Repacking OpenPype version."""
        from openpype.tools.repack_version import VersionRepacker

        version_packer = VersionRepacker(directory)
        version_packer.process()

    def pack_project(self, project_name, dirpath):
        from openpype.lib.project_backpack import pack_project

        pack_project(project_name, dirpath)

    def unpack_project(self, zip_filepath, new_root):
        from openpype.lib.project_backpack import unpack_project

        unpack_project(zip_filepath, new_root)
