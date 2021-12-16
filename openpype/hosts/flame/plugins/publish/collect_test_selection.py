import pyblish.api
import openpype.hosts.flame as opflame
from openpype.hosts.flame.otio import flame_export as otio_export
from openpype.hosts.flame.api import lib
from pprint import pformat
reload(lib)
reload(otio_export)

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