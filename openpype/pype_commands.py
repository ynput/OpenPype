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
    find_variant_key
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
    def publish(paths, targets=None):
        """Start headless publishing.

        Publish use json from passed paths argument.

        Args:
            paths (list): Paths to jsons.
            targets (string): What module should be targeted
                (to choose validator for example)

        Raises:
            RuntimeError: When there is no path to process.
        """
        if not any(paths):
            raise RuntimeError("No publish paths specified")

        from openpype import install, uninstall
        from openpype.api import Logger

        # Register target and host
        import pyblish.api
        import pyblish.util

        env = get_app_environments_for_context(
            os.environ["AVALON_PROJECT"],
            os.environ["AVALON_ASSET"],
            os.environ["AVALON_TASK"],
            os.environ["AVALON_APP_NAME"]
        )
        os.environ.update(env)

        log = Logger.get_logger()

        install()

        pyblish.api.register_target("filesequence")
        pyblish.api.register_host("shell")

        if targets:
            for target in targets:
                pyblish.api.register_target(target)

        os.environ["OPENPYPE_PUBLISH_DATA"] = os.pathsep.join(paths)

        log.info("Running publish ...")

        # Error exit as soon as any error occurs.
        error_format = "Failed {plugin.__name__}: {error} -- {error.traceback}"

        for result in pyblish.util.publish_iter():
            if result["error"]:
                log.error(error_format.format(**result))
                uninstall()
                sys.exit(1)

        log.info("Publish finished.")
        uninstall()

    @staticmethod
    def remotepublishfromapp(project, batch_dir, host, user, targets=None):
        """Opens installed variant of 'host' and run remote publish there.

            Currently implemented and tested for Photoshop where customer
            wants to process uploaded .psd file and publish collected layers
            from there.

            Checks if no other batches are running (status =='in_progress). If
            so, it sleeps for SLEEP (this is separate process),
            waits for WAIT_FOR seconds altogether.

            Requires installed host application on the machine.

            Runs publish process as user would, in automatic fashion.
        """
        SLEEP = 5  # seconds for another loop check for concurrently runs
        WAIT_FOR = 300  # seconds to wait for conc. runs

        from openpype.api import Logger
        from openpype.lib import ApplicationManager

        log = Logger.get_logger()

        log.info("remotepublishphotoshop command")

        application_manager = ApplicationManager()

        found_variant_key = find_variant_key(application_manager, host)

        app_name = "{}/{}".format(host, found_variant_key)

        batch_data = None
        if batch_dir and os.path.exists(batch_dir):
            batch_data = parse_json(os.path.join(batch_dir, "manifest.json"))

        if not batch_data:
            raise ValueError(
                "Cannot parse batch meta in {} folder".format(batch_dir))

        asset, task_name, _task_type = get_batch_asset_task_info(
            batch_data["context"])

        # processing from app expects JUST ONE task in batch and 1 workfile
        task_dir_name = batch_data["tasks"][0]
        task_data = parse_json(os.path.join(batch_dir, task_dir_name,
                                            "manifest.json"))

        workfile_path = os.path.join(batch_dir,
                                     task_dir_name,
                                     task_data["files"][0])

        print("workfile_path {}".format(workfile_path))

        _, batch_id = os.path.split(batch_dir)
        dbcon = get_webpublish_conn()
        # safer to start logging here, launch might be broken altogether
        _id = start_webpublish_log(dbcon, batch_id, user)

        in_progress = True
        slept_times = 0
        while in_progress:
            batches_in_progress = list(dbcon.find({
                "status": "in_progress"
            }))
            if len(batches_in_progress) > 1:
                if slept_times * SLEEP >= WAIT_FOR:
                    fail_batch(_id, batches_in_progress, dbcon)

                print("Another batch running, sleeping for a bit")
                time.sleep(SLEEP)
                slept_times += 1
            else:
                in_progress = False

        # must have for proper launch of app
        env = get_app_environments_for_context(
            project,
            asset,
            task_name,
            app_name
        )
        os.environ.update(env)

        os.environ["OPENPYPE_PUBLISH_DATA"] = batch_dir
        os.environ["IS_HEADLESS"] = "true"
        # must pass identifier to update log lines for a batch
        os.environ["BATCH_LOG_ID"] = str(_id)

        data = {
            "last_workfile_path": workfile_path,
            "start_last_workfile": True
        }

        launched_app = application_manager.launch(app_name, **data)

        while launched_app.poll() is None:
            time.sleep(0.5)

    @staticmethod
    def remotepublish(project, batch_path, user, targets=None):
        """Start headless publishing.

        Used to publish rendered assets, workfiles etc.

        Publish use json from passed paths argument.

        Args:
            project (str): project to publish (only single context is expected
                per call of remotepublish
            batch_path (str): Path batch folder. Contains subfolders with
                resources (workfile, another subfolder 'renders' etc.)
            user (string): email address for webpublisher
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
        import avalon.api
        from openpype.hosts.webpublisher import api as webpublisher

        log = PypeLogger.get_logger()

        log.info("remotepublish command")

        host_name = "webpublisher"
        os.environ["OPENPYPE_PUBLISH_DATA"] = batch_path
        os.environ["AVALON_PROJECT"] = project
        os.environ["AVALON_APP"] = host_name

        pyblish.api.register_host(host_name)

        if targets:
            if isinstance(targets, str):
                targets = [targets]
            for target in targets:
                pyblish.api.register_target(target)

        avalon.api.install(webpublisher)

        log.info("Running publish ...")

        _, batch_id = os.path.split(batch_path)
        dbcon = get_webpublish_conn()
        _id = start_webpublish_log(dbcon, batch_id, user)

        publish_and_log(dbcon, _id, log)

        log.info("Publish finished.")

    @staticmethod
    def extractenvironments(output_json_path, project, asset, task, app):
        env = os.environ.copy()
        if all((project, asset, task, app)):
            from openpype.api import get_app_environments_for_context
            env = get_app_environments_for_context(
                project, asset, task, app, env
            )

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

    def run_tests(self, folder, mark, pyargs):
        """
            Runs tests from 'folder'

            Args:
                 folder (str): relative path to folder with tests
                 mark (str): label to run tests marked by it (slow etc)
                 pyargs (str): package path to test
        """
        print("run_tests")
        import subprocess

        if folder:
            folder = " ".join(list(folder))
        else:
            folder = "../tests"

        mark_str = pyargs_str = ''
        if mark:
            mark_str = "-m {}".format(mark)

        if pyargs:
            pyargs_str = "--pyargs {}".format(pyargs)

        cmd = "pytest {} {} {}".format(folder, mark_str, pyargs_str)
        print("Running {}".format(cmd))
        subprocess.run(cmd)
