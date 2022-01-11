import pyblish.api
import openpype.hosts.flame.api as opfapi
from openpype.hosts.flame.otio import flame_export


class PrecollecTimelineOCIO(pyblish.api.ContextPlugin):
    """Inject the current working context into publish context"""

    label = "Precollect Timeline OTIO"
    order = pyblish.api.CollectorOrder - 0.5

    def process(self, context):
        project = opfapi.get_current_project()
        sequence = opfapi.get_current_sequence(opfapi.CTX.selection)

        # adding otio timeline to context
        otio_timeline = flame_export.create_otio_timeline(sequence)

        # update context with main project attributes
        context.data.update({
            "otioTimeline": otio_timeline,
            "currentFile": "Flame/{}/{}".format(
                project.name, sequence.name
            ),
            "fps": float(str(sequence.frame_rate)[:-4])
        })
