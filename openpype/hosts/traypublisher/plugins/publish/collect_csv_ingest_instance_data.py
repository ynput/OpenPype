from pprint import pformat
import pyblish.api
from openpype.pipeline import publish


class CollectCSVIngestInstancesData(
    pyblish.api.InstancePlugin,
    publish.OpenPypePyblishPluginMixin,
    publish.ColormanagedPyblishPluginMixin
):
    """Collect CSV Ingest data from instance.
    """

    label = "Collect CSV Ingest instances data"
    order = pyblish.api.CollectorOrder
    hosts = ["traypublisher"]
    families = ["csv"]

    def process(self, instance):
        self.log.info(f"Collecting {instance.name}")

        representations = instance.data["transientData"]["representations"]
        instance.data["representations"] = representations

        self.log.debug(pformat(instance.data))
