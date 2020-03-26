import nuke
import pyblish.api
import os

from avalon.nuke import (
    get_avalon_knob_data,
    add_publish_knob
)


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Collect current script for publish."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Workfile"
    hosts = ['nuke']

    def process(self, context):
        root = nuke.root()

        knob_data = get_avalon_knob_data(root)

        add_publish_knob(root)

        family = "workfile"
        task = os.getenv("AVALON_TASK", None)
        # creating instances per write node
        file_path = context.data["currentFile"]
        staging_dir = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        subset = family + task.capitalize()

        # Get frame range
        first_frame = int(root["first_frame"].getValue())
        last_frame = int(root["last_frame"].getValue())

        handle_start = int(knob_data.get("handleStart", 0))
        handle_end = int(knob_data.get("handleEnd", 0))

        # Get format
        format = root['format'].value()
        resolution_width = format.width()
        resolution_height = format.height()
        pixel_aspect = format.pixelAspect()

        # Create instance
        instance = context.create_instance(subset)
        instance.add(root)

        script_data = {
            "asset": os.getenv("AVALON_ASSET", None),
            "frameStart": first_frame + handle_start,
            "frameEnd": last_frame - handle_end,
            "resolutionWidth": resolution_width,
            "resolutionHeight": resolution_height,
            "pixelAspect": pixel_aspect,

            # backward compatibility
            "handles": handle_start,

            "handleStart": handle_start,
            "handleEnd": handle_end,
            "step": 1,
            "fps": root['fps'].value(),
        }
        context.data.update(script_data)

        # creating instance data
        instance.data.update({
            "subset": subset,
            "label": base_name,
            "name": base_name,
            "publish": root.knob('publish').value(),
            "family": family,
            "families": [family],
            "representations": list()
        })

        # adding basic script data
        instance.data.update(script_data)

        # creating representation
        representation = {
            'name': 'nk',
            'ext': 'nk',
            'files': base_name,
            "stagingDir": staging_dir,
        }

        instance.data["representations"].append(representation)

        self.log.info('Publishing script version')
        context.data["instances"].append(instance)
