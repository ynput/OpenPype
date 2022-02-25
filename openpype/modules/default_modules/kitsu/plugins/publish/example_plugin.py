import os

import gazu

import pyblish.api

import debugpy


class CollectExampleAddon(pyblish.api.ContextPlugin):
    order = pyblish.api.CollectorOrder + 0.4
    label = "Collect Kitsu"

    def process(self, context):
        debugpy.breakpoint()
        self.log.info("I'm in Kitsu's plugin!")


class IntegrateRig(pyblish.api.InstancePlugin):
    """Copy files to an appropriate location where others may reach it"""

    order = pyblish.api.IntegratorOrder
    families = ["model"]

    def process(self, instance):
        print(instance.data["version"])

        # Connect to server
        gazu.client.set_host(os.environ["KITSU_SERVER"])

        # Authenticate
        gazu.log_in(os.environ["KITSU_LOGIN"], os.environ["KITSU_PWD"])

        asset_data = instance.data["assetEntity"]["data"]

        # TODO Set local settings for login and password

        # Get task
        task_type = gazu.task.get_task_type_by_name(instance.data["task"])
        entity_task = gazu.task.get_task_by_entity(asset_data["zou"], task_type)

        # Comment entity
        gazu.task.add_comment(
            entity_task,
            entity_task["task_status_id"],
            comment=f"Version {instance.data['version']} has been published!",
        )

        self.log.info("Copied successfully!")
