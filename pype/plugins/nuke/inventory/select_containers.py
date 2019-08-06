from avalon import api


class SelectContainers(api.InventoryAction):

    label = "Select Containers"
    icon = "mouse-pointer"
    color = "#d8d8d8"

    def process(self, containers):

        import avalon.nuke

        nodes = [i["_node"] for i in containers]

        with avalon.nuke.viewer_update_and_undo_stop():
            # clear previous_selection
            [n['selected'].setValue(False) for n in nodes]
            # Select tool
            for node in nodes:
                node["selected"].setValue(True)
