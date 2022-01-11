import pyblish.api
import avalon.api as avalon
import openpype.hosts.flame.api as opfapi
from openpype.hosts.flame.otio import flame_export


class PrecollecTimelineOCIO(pyblish.api.ContextPlugin):
    """Inject the current working context into publish context"""

    label = "Precollect Timeline OTIO"
    order = pyblish.api.CollectorOrder - 0.5

    def process(self, context):
        asset = avalon.Session["AVALON_ASSET"]
        subset = "otioTimeline"
        project = opfapi.get_current_project()
        sequence = opfapi.get_current_sequence(opfapi.CTX.selection)

        # adding otio timeline to context
        otio_timeline = flame_export.create_otio_timeline(sequence)

        instance_data = {
            "name": "{}_{}".format(asset, subset),
            "asset": asset,
            "subset": "{}{}".format(asset, subset.capitalize()),
            "family": "workfile"
        }

        # create instance with workfile
        instance = context.create_instance(**instance_data)
        self.log.info("Creating instance: {}".format(instance))

        # update context with main project attributes
        context.data.update({
            "otioTimeline": otio_timeline,
            "currentFile": "Flame/{}/{}".format(
                project.name, sequence.name
            ),
            "fps": float(str(sequence.frame_rate)[:-4])
        })
