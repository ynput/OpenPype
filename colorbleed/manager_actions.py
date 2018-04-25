from avalon import api, pipeline


class FusionSelectContainer(api.ToolAction):

    label = "Select Container"
    icon = "object-group"
    hosts = ["fusion"]
    tools = ["manager"]

    def process(self, items):

        import avalon.fusion

        tools = [i["_tool"] for i in items]

        comp = avalon.fusion.get_current_comp()
        flow = comp.CurrentFrame.FlowView

        # Clear selection
        flow.Select()

        # Select tool
        for tool in tools:
            flow.Select(tool)


def register_manager_actions():
    pipeline.register_plugin(api.ToolAction, FusionSelectContainer)
