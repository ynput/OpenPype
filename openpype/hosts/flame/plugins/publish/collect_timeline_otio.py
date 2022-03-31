import pyblish.api
import avalon.api as avalon
import openpype.lib as oplib
import openpype.hosts.flame.api as opfapi
from openpype.hosts.flame.otio import flame_export


class CollecTimelineOTIO(pyblish.api.ContextPlugin):
    """Inject the current working context into publish context"""

    label = "Collect Timeline OTIO"
    order = pyblish.api.CollectorOrder - 0.099

    def process(self, context):
        # plugin defined
        family = "workfile"
        variant = "otioTimeline"

        # main
        asset_doc = context.data["assetEntity"]
        task_name = avalon.Session["AVALON_TASK"]
        project = opfapi.get_current_project()
        sequence = opfapi.get_current_sequence(opfapi.CTX.selection)

        # create subset name
        subset_name = oplib.get_subset_name_with_asset_doc(
            family,
            variant,
            task_name,
            asset_doc,
        )

        # adding otio timeline to context
        with opfapi.maintained_segment_selection(sequence) as selected_seg:
            otio_timeline = flame_export.create_otio_timeline(sequence)

            instance_data = {
                "name": subset_name,
                "asset": asset_doc["name"],
                "subset": subset_name,
                "family": "workfile"
            }

            # create instance with workfile
            instance = context.create_instance(**instance_data)
            self.log.info("Creating instance: {}".format(instance))

            # update context with main project attributes
            context.data.update({
                "flameProject": project,
                "flameSequence": sequence,
                "otioTimeline": otio_timeline,
                "currentFile": "Flame/{}/{}".format(
                    project.name, sequence.name
                ),
                "flameSelectedSegments": selected_seg,
                "fps": float(str(sequence.frame_rate)[:-4])
            })
