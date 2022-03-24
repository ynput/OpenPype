from openpype.pipeline import InventoryAction
from openpype.hosts.nuke.api.commands import viewer_update_and_undo_stop


class SelectContainers(InventoryAction):

    label = "Select Containers"
    icon = "mouse-pointer"
    color = "#d8d8d8"

    def process(self, containers):
        import nuke

        nodes = [nuke.toNode(i["objectName"]) for i in containers]

        with viewer_update_and_undo_stop():
            # clear previous_selection
            [n['selected'].setValue(False) for n in nodes]
            # Select tool
            for node in nodes:
                node["selected"].setValue(True)
