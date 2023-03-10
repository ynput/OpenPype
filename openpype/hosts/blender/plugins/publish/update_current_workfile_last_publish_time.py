import pyblish.api
import bpy


class UpdateCurrentWorkfileLastPublishTime(pyblish.api.ContextPlugin):
    """Update current workfile last published time.

    Used to ensure current workfile is up to date with published workfiles.
    """

    order = pyblish.api.IntegratorOrder + 0.00002
    hosts = ["blender"]
    families = ["workfile"]
    label = "Update Current Workfile Last Publish Time"
    optional = False

    def process(self, context):
        scene = bpy.context.scene
        scene["op_published_time"] = context.data["time"]
        scene.is_workfile_up_to_date = True
