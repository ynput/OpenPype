from maya import cmds

from openpype.pipeline import InventoryAction, registered_host
from openpype.hosts.maya.api.lib import get_container_members


class SelectInScene(InventoryAction):
    """Select nodes in the scene from selected containers in scene inventory"""

    label = "Select In Scene"
    icon = "search"
    color = "#888888"
    order = 99

    def process(self, containers):

        all_members = []
        for container in containers:
            members = get_container_members(container)
            all_members.extend(members)
        cmds.select(all_members, replace=True, noExpand=True)


class SelectFromScene(InventoryAction):
    """Select containers in scene inventory from the current scene selection"""

    label = "Select From Scene"
    icon = "search"
    color = "#888888"
    order = 100

    def process(self, containers):

        selection = set(cmds.ls(selection=True, long=True, objectsOnly=True))
        host = registered_host()

        to_select = []
        for container in host.get_containers():
            members = get_container_members(container)
            if any(member in selection for member in members):
                to_select.append(container["objectName"])

        return {
            "objectNames": to_select,
            "options": {"clear": True}
        }
