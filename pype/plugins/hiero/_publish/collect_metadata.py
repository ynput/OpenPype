from pyblish import api


class CollectClipMetadata(api.InstancePlugin):
    """Collect Metadata from selected track items."""

    order = api.CollectorOrder + 0.01
    label = "Collect Metadata"
    hosts = ["hiero"]

    def process(self, instance):
        item = instance.data["item"]
        ti_metadata = self.metadata_to_string(dict(item.metadata()))
        ms_metadata = self.metadata_to_string(
            dict(item.source().mediaSource().metadata()))

        instance.data["clipMetadata"] = ti_metadata
        instance.data["mediaSourceMetadata"] = ms_metadata

        self.log.info(instance.data["clipMetadata"])
        self.log.info(instance.data["mediaSourceMetadata"])
        return

    def metadata_to_string(self, metadata):
        data = dict()
        for k, v in metadata.items():
            if v not in ["-", ""]:
                data[str(k)] = v

        return data
