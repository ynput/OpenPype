import pyblish.api

import pype.lib
from avalon.tools import cbsceneinventory


class ShowInventory(pyblish.api.Action):

    label = "Show Inventory"
    icon = "briefcase"
    on = "failed"

    def process(self, context, plugin):
        cbsceneinventory.show()


class ValidateContainers(pyblish.api.ContextPlugin):
    """Containers are must be updated to latest version on publish."""

    label = "Validate Containers"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya", "houdini", "nuke", "harmony", "photoshop"]
    optional = True
    actions = [ShowInventory]

    def process(self, context):
        if pype.lib.any_outdated():
            raise ValueError("There are outdated containers in the scene.")
