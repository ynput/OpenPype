import pyblish
import openpype.hosts.flame.api as opfapi

@pyblish.api.log
class IntegrateBatchGroup(pyblish.api.InstancePlugin):
    """Integrate published shot to batch group"""

    order = pyblish.api.IntegratorOrder + 0.45
    label = "Integrate Batch Groups"
    hosts = ["flame"]
    families = ["clip"]

    def process(self, instance):
        opfapi.create_batch