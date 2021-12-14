import pyblish.api
import openpype.hosts.flame as opflame
from openpype.hosts.flame.otio import flame_export as otio_export
import flame
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
        otio_export.create_otio_timeline(opflame.selection)