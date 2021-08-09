import os
import pyblish.api


class ExtractResources(pyblish.api.InstancePlugin):
    """
        Extracts files from instance.data["resources"].

        These files are additional (textures etc.), currently not stored in
        representations!

        Expects collected 'resourcesDir'. (list of dicts with 'files' key and
            list of source urls)

        Provides filled 'transfers' (list of tuples (source_url, target_url))
    """

    label = "Extract Resources SP"
    hosts = ["standalonepublisher"]
    order = pyblish.api.ExtractorOrder

    families = ["workfile"]

    def process(self, instance):
        if not instance.data.get("resources"):
            self.log.info("No resources")
            return

        if not instance.data.get("transfers"):
            instance.data["transfers"] = []

        publish_dir = instance.data["resourcesDir"]

        transfers = []
        for resource in instance.data["resources"]:
            for file_url in resource.get("files", []):
                file_name = os.path.basename(file_url)
                dest_url = os.path.join(publish_dir, file_name)
                transfers.append((file_url, dest_url))

        self.log.info("transfers:: {}".format(transfers))
        instance.data["transfers"].extend(transfers)
