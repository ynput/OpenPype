from openpype.api import Anatomy
from openpype.lib import (
    PreLaunchHook,
    EnvironmentPrepData,
    prepare_app_environments,
    prepare_context_environments
)

import avalon.api


class GlobalHostDataHook(PreLaunchHook):
    order = -100

    def execute(self):
        """Prepare global objects to `data` that will be used for sure."""
        self.prepare_global_data()

        if not self.data.get("asset_doc"):
            return

        app = self.launch_context.application
        temp_data = EnvironmentPrepData({
            "project_name": self.data["project_name"],
            "asset_name": self.data["asset_name"],
            "task_name": self.data["task_name"],

            "app": app,

            "dbcon": self.data["dbcon"],
            "project_doc": self.data["project_doc"],
            "asset_doc": self.data["asset_doc"],

            "anatomy": self.data["anatomy"],

            "env": self.launch_context.env,

            "start_last_workfile": self.data.get("start_last_workfile"),
            "last_workfile_path": self.data.get("last_workfile_path"),

            "log": self.log
        })

        prepare_app_environments(temp_data, self.launch_context.env_group)
        prepare_context_environments(temp_data)

        temp_data.pop("log")

        self.data.update(temp_data)

    def prepare_global_data(self):
        """Prepare global objects to `data` that will be used for sure."""
        # Mongo documents
        project_name = self.data.get("project_name")
        if not project_name:
            self.log.info(
                "Skipping global data preparation."
                " Key `project_name` was not found in launch context."
            )
            return

        self.log.debug("Project name is set to \"{}\"".format(project_name))
        # Anatomy
        self.data["anatomy"] = Anatomy(project_name)

        # Mongo connection
        dbcon = avalon.api.AvalonMongoDB()
        dbcon.Session["AVALON_PROJECT"] = project_name
        dbcon.install()

        self.data["dbcon"] = dbcon

        # Project document
        project_doc = dbcon.find_one({"type": "project"})
        self.data["project_doc"] = project_doc

        asset_name = self.data.get("asset_name")
        if not asset_name:
            self.log.warning(
                "Asset name was not set. Skipping asset document query."
            )
            return

        asset_doc = dbcon.find_one({
            "type": "asset",
            "name": asset_name
        })
        self.data["asset_doc"] = asset_doc
