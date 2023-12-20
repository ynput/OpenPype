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
    order = pyblish.api.CollectorOrder + 0.1
    hosts = ["traypublisher"]
    families = ["csv"]

    def process(self, instance):
        self.log.info(f"Collecting {instance.name}")

        # expecting [(colorspace, repre_data), ...]
        prepared_repres_data_items = instance.data[
            "prepared_data_for_repres"]

        for colorspace, repre_data in prepared_repres_data_items:
            # only apply colorspace to those which are not marked as thumbnail
            if colorspace != "_thumbnail_":
                # colorspace name is passed from CSV column
                self.set_representation_colorspace(
                    repre_data, instance.context, colorspace
                )

            instance.data["representations"].append(repre_data)

        self.log.debug(pformat(instance.data))
