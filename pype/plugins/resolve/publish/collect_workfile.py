import os
import pyblish.api
from pype.hosts import resolve
from avalon import api as avalon
from pprint import pformat


class CollectWorkfile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    label = "Collect Workfile"
    order = pyblish.api.CollectorOrder - 0.501

    def process(self, context):
        exported_projet_ext = ".drp"
        asset = avalon.Session["AVALON_ASSET"]
        staging_dir = os.getenv("AVALON_WORKDIR")
        subset = "workfile"

        project = resolve.get_current_project()
        name = project.GetName()
        fps = project.GetSetting("timelineFrameRate")

        base_name = name + exported_projet_ext
        current_file = os.path.join(staging_dir, base_name)
        current_file = os.path.normpath(current_file)

        active_sequence = resolve.get_current_sequence()
        video_tracks = resolve.get_video_track_names()

        # set main project attributes to context
        context.data.update({
            "activeProject": project,
            "activeSequence": active_sequence,
            "videoTracks": video_tracks,
            "currentFile": current_file,
            "fps": fps,
        })

        # creating workfile representation
        representation = {
            'name': exported_projet_ext[1:],
            'ext': exported_projet_ext[1:],
            'files': base_name,
            "stagingDir": staging_dir,
        }

        instance_data = {
            "name": "{}_{}".format(asset, subset),
            "asset": asset,
            "subset": "{}{}".format(asset, subset.capitalize()),
            "item": project,
            "family": "workfile",

            # source attribute
            "sourcePath": current_file,
            "representations": [representation]
        }

        instance = context.create_instance(**instance_data)
        self.log.info("Creating instance: {}".format(instance))
        self.log.debug("__ instance.data: {}".format(pformat(instance.data)))
