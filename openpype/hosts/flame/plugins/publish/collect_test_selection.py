import pyblish.api
import openpype.hosts.flame as opflame
from openpype.hosts.flame.otio import flame_export as otio_export
from openpype.hosts.flame.api import lib
from pprint import pformat
reload(lib)  # noqa
reload(otio_export)  # noqa


@pyblish.api.log
class CollectTestSelection(pyblish.api.ContextPlugin):
    """testing selection sharing
    """

    order = pyblish.api.CollectorOrder
    label = "test selection"
    hosts = ["flame"]

    def process(self, context):
        self.log.info(opflame.selection)

        sequence = lib.get_current_sequence(opflame.selection)

        otio_timeline = otio_export.create_otio_timeline(sequence)

        self.log.info(pformat(otio_timeline))

        # test segment markers
        for ver in sequence.versions:
            for track in ver.tracks:
                if len(track.segments) == 0 and track.hidden:
                    continue

                for segment in track.segments:
                    if str(segment.name)[1:-1] == "":
                        continue
                    if not segment.selected:
                        continue

                    self.log.debug("Segment with OpenPypeData: {}".format(
                        segment.name))

                    lib.imprint(segment, {
                        'asset': 'sq020sh0280',
                        'family': 'render',
                        'subset': 'subsetMain'
                    })
