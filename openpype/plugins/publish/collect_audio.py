import pyblish.api
from pprint import pformat

from openpype.client import (
    get_last_version_by_subset_name,
    get_representations,
)
from openpype.pipeline import (
    legacy_io,
    get_representation_path,
)


class CollectAudio(pyblish.api.InstancePlugin):

    label = "Colect Audio"
    order = pyblish.api.CollectorOrder + 0.1
    hosts = ["standalonepublisher"]

    def process(self, instance):
        self.log.info('Collecting Audio Data')

        project_name = legacy_io.active_project()
        asset_name = instance.data["asset"]
        # * Add audio to instance if exists.
        # Find latest versions document
        last_version_doc = get_last_version_by_subset_name(
            project_name, "audioMain", asset_name=asset_name, fields=["_id"]
        )

        repre_doc = None
        if last_version_doc:
            # Try to find it's representation (Expected there is only one)
            repre_docs = list(get_representations(
                project_name, version_ids=[last_version_doc["_id"]]
            ))
            if not repre_docs:
                self.log.warning(
                    "Version document does not contain any representations"
                )
            else:
                repre_doc = repre_docs[0]

        # Add audio to instance if representation was found
        if repre_doc:
            instance.data["audio"] = [{
                "offset": 0,
                "filename": get_representation_path(repre_doc)
            }]

        self.log.debug("instance.data: {}".format(pformat(instance.data)))
