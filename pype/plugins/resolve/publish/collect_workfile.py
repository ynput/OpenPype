import os
import pyblish.api
from pype.hosts import resolve
from avalon import api as avalon
from pprint import pformat

# dev
from importlib import reload
from pype.hosts.resolve import otio
reload(otio)


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

        # adding otio timeline to context
        otio_timeline = resolve.get_otio_complete_timeline(project)

        base_name = name + exported_projet_ext
        current_file = os.path.join(staging_dir, base_name)
        current_file = os.path.normpath(current_file)

        active_sequence = resolve.get_current_sequence()
        video_tracks = resolve.get_video_track_names()

        # set main project attributes to context
        context_data = {
            "activeProject": project,
            "activeSequence": active_sequence,
            "otioTimeline": otio_timeline,
            "videoTracks": video_tracks,
            "currentFile": current_file,
            "fps": fps,
        }
        self.log.debug("__ context_data: {}".format(pformat(context_data)))
        context.data.update(context_data)

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

        file_name = "".join([asset, "_", subset, ".otio"])
        file_path = os.path.join(staging_dir, file_name)
        resolve.save_otio(otio_timeline, file_path)
