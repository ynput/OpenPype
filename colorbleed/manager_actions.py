from avalon import api, pipeline


class FusionSelectContainer(api.InventoryAction):

    label = "Select Container"
    icon = "mouse-pointer"
    color = "#d8d8d8"
    hosts = ["fusion"]
    tools = ["manager"]

    def process(self, containers):

        import avalon.fusion

        tools = [i["_tool"] for i in containers]

        comp = avalon.fusion.get_current_comp()
        flow = comp.CurrentFrame.FlowView

        with avalon.fusion.comp_lock_and_undo_chunk(comp, self.label):
            # Clear selection
            flow.Select()

            # Select tool
            for tool in tools:
                flow.Select(tool)


def register_manager_actions():
    pipeline.register_plugin(api.InventoryAction, FusionSelectContainer)
