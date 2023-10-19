import os
import nuke
import pyblish.api
from openpype.lib import get_version_from_path
import openpype.hosts.nuke.api as napi
from openpype.pipeline import KnownPublishError


class CollectContextData(pyblish.api.ContextPlugin):
    """Collect current context publish."""

    order = pyblish.api.CollectorOrder - 0.499
    label = "Collect context data"
    hosts = ['nuke']

    def process(self, context):  # sourcery skip: avoid-builtin-shadow
        root_node = nuke.root()

        current_file = os.path.normpath(root_node.name())

        if current_file.lower() == "root":
            raise KnownPublishError(
                "Workfile is not correct file name. \n"
                "Use workfile tool to manage the name correctly."
            )

        # Get frame range
        first_frame = int(root_node["first_frame"].getValue())
        last_frame = int(root_node["last_frame"].getValue())

        # get instance data from root
        root_instance_context = napi.get_node_data(
            root_node, napi.INSTANCE_DATA_KNOB
        )

        handle_start = root_instance_context["handleStart"]
        handle_end = root_instance_context["handleEnd"]

        # Get format
        format = root_node['format'].value()
        resolution_width = format.width()
        resolution_height = format.height()
        pixel_aspect = format.pixelAspect()

        script_data = {
            "frameStart": first_frame + handle_start,
            "frameEnd": last_frame - handle_end,
            "resolutionWidth": resolution_width,
            "resolutionHeight": resolution_height,
            "pixelAspect": pixel_aspect,

            "handleStart": handle_start,
            "handleEnd": handle_end,
            "step": 1,
            "fps": root_node['fps'].value(),

            "currentFile": current_file,
            "version": int(get_version_from_path(current_file)),

            "host": pyblish.api.current_host(),
            "hostVersion": nuke.NUKE_VERSION_STRING
        }

        context.data["scriptData"] = script_data
        context.data.update(script_data)

        self.log.debug('Context from Nuke script collected')
