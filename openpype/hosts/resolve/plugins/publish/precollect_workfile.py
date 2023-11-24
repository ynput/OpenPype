import pyblish.api
from pprint import pformat

from openpype import AYON_SERVER_ENABLED
from openpype.pipeline import get_current_asset_name

from openpype.hosts.resolve import api as rapi
from openpype.hosts.resolve.otio import davinci_export


class PrecollectWorkfile(pyblish.api.ContextPlugin):
    """Precollect the current working file into context"""

    label = "Precollect Workfile"
    order = pyblish.api.CollectorOrder - 0.5

    def process(self, context):
        current_asset_name = asset_name = get_current_asset_name()

        if AYON_SERVER_ENABLED:
            asset_name = current_asset_name.split("/")[-1]

        subset = "workfileMain"
        project = rapi.get_current_project()
        fps = project.GetSetting("timelineFrameRate")
        video_tracks = rapi.get_video_track_names()

        # adding otio timeline to context
        otio_timeline = davinci_export.create_otio_timeline(project)

        instance_data = {
            "name": "{}_{}".format(asset_name, subset),
            "label": "{} {}".format(current_asset_name, subset),
            "asset": current_asset_name,
            "subset": subset,
            "item": project,
            "family": "workfile",
            "families": []
        }

        # create instance with workfile
        instance = context.create_instance(**instance_data)

        # update context with main project attributes
        context_data = {
            "activeProject": project,
            "otioTimeline": otio_timeline,
            "videoTracks": video_tracks,
            "currentFile": project.GetName(),
            "fps": fps,
        }
        context.data.update(context_data)

        self.log.info("Creating instance: {}".format(instance))
        self.log.debug("__ instance.data: {}".format(pformat(instance.data)))
        self.log.debug("__ context_data: {}".format(pformat(context_data)))
