import pyblish.api
import nuke


class ValidateActiveViewer(pyblish.api.ContextPlugin):
    """Validate presentse of the active viewer from nodes
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Active Viewer"
    hosts = ["nuke"]

    def process(self, context):
        viewer_process_node = context.data.get("ViewerProcess")

        assert viewer_process_node, (
            "Missing active viewer process! Please click on output write node and push key number 1-9"
        )
        active_viewer = context.data["ActiveViewer"]
        active_input = active_viewer.activeInput()

        assert active_input is not None, (
            "Missing active viewer input! Please click on output write node and push key number 1-9"
        )
