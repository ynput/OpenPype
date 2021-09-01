# -*- coding: utf-8 -*-
"""Implementation of Pype commands."""
import os
import sys
import json
from datetime import datetime

from openpype.lib import PypeLogger
from openpype.api import get_app_environments_for_context


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
    def remotepublish(project, batch_path, host, user, targets=None):
        """Start headless publishing.

        Publish use json from passed paths argument.

        Args:
            project (str): project to publish (only single context is expected
                per call of remotepublish
            batch_path (str): Path batch folder. Contains subfolders with
                resources (workfile, another subfolder 'renders' etc.)
            targets (string): What module should be targeted
                (to choose validator for example)
            host (string)
            user (string): email address for webpublisher

        Raises:
            RuntimeError: When there is no path to process.
        """
        if not batch_path:
            raise RuntimeError("No publish paths specified")

        from openpype import install, uninstall
        from openpype.api import Logger
        from openpype.lib import OpenPypeMongoConnection

        # Register target and host
        import pyblish.api
        import pyblish.util

        log = Logger.get_logger()

        log.info("remotepublish command")

        install()

        if host:
            pyblish.api.register_host(host)

        if targets:
            if isinstance(targets, str):
                targets = [targets]
            for target in targets:
                pyblish.api.register_target(target)

        os.environ["OPENPYPE_PUBLISH_DATA"] = batch_path
        os.environ["AVALON_PROJECT"] = project
        os.environ["AVALON_APP"] = host

        import avalon.api
        from openpype.hosts.webpublisher import api as webpublisher

        avalon.api.install(webpublisher)

        log.info("Running publish ...")

        # Error exit as soon as any error occurs.
        error_format = "Failed {plugin.__name__}: {error} -- {error.traceback}"

        mongo_client = OpenPypeMongoConnection.get_mongo_client()
        database_name = os.environ["OPENPYPE_DATABASE_NAME"]
        dbcon = mongo_client[database_name]["webpublishes"]

        _, batch_id = os.path.split(batch_path)
        _id = dbcon.insert_one({
            "batch_id": batch_id,
            "start_date": datetime.now(),
            "user": user,
            "status": "in_progress"
        }).inserted_id

        log_lines = []
        for result in pyblish.util.publish_iter():
            for record in result["records"]:
                log_lines.append("{}: {}".format(
                    result["plugin"].label, record.msg))

            if result["error"]:
                log.error(error_format.format(**result))
                uninstall()
                log_lines.append(error_format.format(**result))
                dbcon.update_one(
                    {"_id": _id},
                    {"$set":
                        {
                            "finish_date": datetime.now(),
                            "status": "error",
                            "log": os.linesep.join(log_lines)

                        }}
                )
                sys.exit(1)
            else:
                dbcon.update_one(
                    {"_id": _id},
                    {"$set":
                        {
                            "progress": max(result["progress"], 0.95),
                            "log": os.linesep.join(log_lines)
                        }}
                )

        dbcon.update_one(
            {"_id": _id},
            {"$set":
                {
                    "finish_date": datetime.now(),
                    "status": "finished_ok",
                    "progress": 1,
                    "log": os.linesep.join(log_lines)
                }}
        )

        log.info("Publish finished.")
        uninstall()

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

    def texture_copy(self, project, asset, path):
        pass

    def run_application(self, app, project, asset, task, tools, arguments):
        pass

    def validate_jsons(self):
        pass

