import pyblish.api
import openpype.hosts.flame as opflame
import flame

@pyblish.api.log
class CollectTestSelection(pyblish.api.ContextPlugin):
    """testing selection sharing
    """

    order = pyblish.api.CollectorOrder
    label = "test selection"
    hosts = ["flame"]

    def process(self, context):
        self.log.info(opflame.selection)