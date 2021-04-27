import pyblish.api
import hiero.ui
from openpype.hosts.hiero import api as phiero
from avalon import api as avalon
from pprint import pformat
from openpype.hosts.hiero.otio import hiero_export


class PrecollectWorkfile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    label = "Precollect Workfile"
    order = pyblish.api.CollectorOrder - 0.6

    def process(self, context):

        asset = avalon.Session["AVALON_ASSET"]
        subset = "workfile"
        project = phiero.get_current_project()
        active_timeline = hiero.ui.activeSequence()
        fps = active_timeline.framerate().toFloat()

        # adding otio timeline to context
        otio_timeline = hiero_export.create_otio_timeline()

        instance_data = {
            "name": "{}_{}".format(asset, subset),
            "asset": asset,
            "subset": "{}{}".format(asset, subset.capitalize()),
            "item": project,
            "family": "workfile"
        }

        # create instance with workfile
        instance = context.create_instance(**instance_data)

        # update context with main project attributes
        context_data = {
            "activeProject": project,
            "otioTimeline": otio_timeline,
            "currentFile": project.path(),
            "fps": fps,
        }
        context.data.update(context_data)

        self.log.info("Creating instance: {}".format(instance))
        self.log.debug("__ instance.data: {}".format(pformat(instance.data)))
        self.log.debug("__ context_data: {}".format(pformat(context_data)))
