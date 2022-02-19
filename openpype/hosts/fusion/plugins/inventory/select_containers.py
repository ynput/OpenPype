from avalon import api


class FusionSelectContainers(api.InventoryAction):

    label = "Select Containers"
    icon = "mouse-pointer"
    color = "#d8d8d8"

    def process(self, containers):
        from openpype.hosts.fusion.api import (
            get_current_comp,
            comp_lock_and_undo_chunk
        )

        tools = [i["_tool"] for i in containers]

        comp = get_current_comp()
        flow = comp.CurrentFrame.FlowView

        with comp_lock_and_undo_chunk(comp, self.label):
            # Clear selection
            flow.Select()

            # Select tool
            for tool in tools:
                flow.Select(tool)
