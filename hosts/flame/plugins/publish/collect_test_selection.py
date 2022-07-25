import os
import pyblish.api
import tempfile
import openpype.hosts.flame.api as opfapi
from openpype.hosts.flame.otio import flame_export as otio_export
import opentimelineio as otio
from pprint import pformat
reload(otio_export)  # noqa


@pyblish.api.log
class CollectTestSelection(pyblish.api.ContextPlugin):
    """testing selection sharing
    """

    order = pyblish.api.CollectorOrder
    label = "test selection"
    hosts = ["flame"]
    active = False

    def process(self, context):
        self.log.info(
            "Active Selection: {}".format(opfapi.CTX.selection))

        sequence = opfapi.get_current_sequence(opfapi.CTX.selection)

        self.test_imprint_data(sequence)
        self.test_otio_export(sequence)

    def test_otio_export(self, sequence):
        test_dir = os.path.normpath(
            tempfile.mkdtemp(prefix="test_pyblish_tmp_")
        )
        export_path = os.path.normpath(
            os.path.join(
                test_dir, "otio_timeline_export.otio"
            )
        )
        otio_timeline = otio_export.create_otio_timeline(sequence)
        otio_export.write_to_file(
            otio_timeline, export_path
        )
        read_timeline_otio = otio.adapters.read_from_file(export_path)

        if otio_timeline != read_timeline_otio:
            raise Exception("Exported timeline is different from original")

        self.log.info(pformat(otio_timeline))
        self.log.info("Otio exported to: {}".format(export_path))

    def test_imprint_data(self, sequence):
        with opfapi.maintained_segment_selection(sequence) as sel_segments:
            for segment in sel_segments:
                if str(segment.name)[1:-1] == "":
                    continue

                self.log.debug("Segment with OpenPypeData: {}".format(
                    segment.name))

                opfapi.imprint(segment, {
                    'asset': segment.name.get_value(),
                    'family': 'render',
                    'subset': 'subsetMain'
                })
