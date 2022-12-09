import pyblish.api
import bpy


class UpdateCurrentWorkfileLastPublishTime(pyblish.api.ContextPlugin):
    """Update current workfile last published time.

    Used to ensure current workfile is up to date with published workfiles.
    """

    order = pyblish.api.IntegratorOrder + 10
    hosts = ["blender"]
    families = ["workfile"]
    label = "Update Current Workfile Last Publish Time"
    optional = False

    def process(self, context):
        bpy.context.window_manager.current_workfile_last_publish_time = (
            context.data["time"]
        )
