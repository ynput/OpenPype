import os
import pyblish.api
import openpype.hosts.flame as opflame
from openpype.hosts.flame.otio import flame_export as otio_export
from openpype.hosts.flame.api import lib, pipeline
from pprint import pformat
reload(lib)  # noqa
reload(pipeline)  # noqa
reload(otio_export)  # noqa


@pyblish.api.log
class CollectTestSelection(pyblish.api.ContextPlugin):
    """testing selection sharing
    """

    order = pyblish.api.CollectorOrder
    label = "test selection"
    hosts = ["flame"]

    def process(self, context):
        self.log.info(
            "Active Selection: {}".format(opflame.selection))

        sequence = lib.get_current_sequence(opflame.selection)

        self.test_imprint_data(sequence)
        self.test_otio_export(sequence)

    def test_otio_export(self, sequence):
        home_dir = os.path.expanduser("~")
        export_path = os.path.normalize(
            os.path.join(
                home_dir, "otio_timeline_export.otio"
            )
        )
        otio_timeline = otio_export.create_otio_timeline(sequence)
        otio_export.write_to_file(
            otio_timeline, export_path
            )

        self.log.info(pformat(otio_timeline))
        self.log.info("Otio exported to: {}".format(export_path))

    def test_imprint_data(self, sequence):
        with lib.maintained_segment_selection(sequence) as selected_segments:
            for segment in selected_segments:
                if str(segment.name)[1:-1] == "":
                    continue

                self.log.debug("Segment with OpenPypeData: {}".format(
                    segment.name))

                pipeline.imprint(segment, {
                    'asset': segment.name.get_value(),
                    'family': 'render',
                    'subset': 'subsetMain'
                })
