from maya import cmds

from avalon import api


class ImportReference(api.InventoryAction):
    """Imports selected reference inside the file."""

    label = "Import Reference"
    icon = "mouse-pointer"
    color = "#d8d8d8"

    def process(self, containers):
        references = cmds.ls(type="reference")

        for container in containers:
            if container["loader"] != "ReferenceLoader":
                print("Not a reference, skipping")
                continue

            reference_name = container["namespace"] + "RN"
            if reference_name in references:
                print("Importing {}".format(reference_name))

                ref_file = cmds.referenceQuery(reference_name, f=True)

                cmds.file(ref_file, importReference=True)

        return "refresh"
