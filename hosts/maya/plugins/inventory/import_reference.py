from maya import cmds

from openpype.pipeline import InventoryAction
from openpype.hosts.maya.api.plugin import get_reference_node


class ImportReference(InventoryAction):
    """Imports selected reference to inside of the file."""

    label = "Import Reference"
    icon = "download"
    color = "#d8d8d8"

    def process(self, containers):
        references = cmds.ls(type="reference")
        for container in containers:
            if container["loader"] != "ReferenceLoader":
                print("Not a reference, skipping")
                continue

            node = container["objectName"]
            members = cmds.sets(node, query=True, nodesOnly=True)
            ref_node = get_reference_node(members)

            ref_file = cmds.referenceQuery(ref_node, f=True)
            cmds.file(ref_file, importReference=True)

        return True  # return anything to trigger model refresh
