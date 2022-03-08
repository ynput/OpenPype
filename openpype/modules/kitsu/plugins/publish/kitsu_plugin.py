import os

import gazu

import pyblish.api


class CollectExampleAddon(pyblish.api.ContextPlugin):
    order = pyblish.api.CollectorOrder + 0.4
    label = "Collect Kitsu"

    def process(self, context):
        self.log.info("I'm in Kitsu's plugin!")


class IntegrateRig(pyblish.api.InstancePlugin):
    """Copy files to an appropriate location where others may reach it"""

    order = pyblish.api.IntegratorOrder
    families = ["model"]

    def process(self, instance):

        # Connect to server
        gazu.client.set_host(os.environ["KITSU_SERVER"])

        # Authenticate
        gazu.log_in(os.environ["KITSU_LOGIN"], os.environ["KITSU_PWD"])

        asset_data = instance.data["assetEntity"]["data"]

        # Get task
        task_type = gazu.task.get_task_type_by_name(instance.data["task"])
        entity_task = gazu.task.get_task_by_entity(
            asset_data["zou"], task_type
        )

        # Comment entity
        gazu.task.add_comment(
            entity_task,
            entity_task["task_status_id"],
            comment="Version {} has been published!\n".format(
                instance.data["version"]
            )
            # Add written comment in Pyblish
            + "\n{}".format(instance.data["versionEntity"]["data"]["comment"]),
        )

        self.log.info("Version published to Kitsu successfully!")
