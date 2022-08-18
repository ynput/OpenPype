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
    """ Collecting available audio subset to instance

    """
    label = "Collect Audio"
    order = pyblish.api.CollectorOrder + 0.1
    families = ["review"]
    hosts = [
        "nuke",
        "maya",
        "shell",
        "hiero",
        "premiere",
        "harmony",
        "traypublisher",
        "standalonepublisher",
        "fusion",
        "tvpaint",
        "resolve",
        "webpublisher",
        "aftereffects",
        "flame",
        "unreal"
    ]

    audio_subset_name = "audioMain"

    def process(self, instance):
        if instance.data.get("audio"):
            self.log.info(
                "Skipping Audio collecion. It is already collected"
            )
            return

        # Add audio to instance if exists.
        self.log.info('Collecting Audio Data ...')

        project_name = legacy_io.active_project()
        asset_name = instance.data["asset"]

        # Find latest versions document
        last_version_doc = get_last_version_by_subset_name(
            project_name,
            self.audio_subset_name,
            asset_name=asset_name,
            fields=["_id"]
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
            self.log.info("Audio Data added to instance ...")

        self.log.debug("instance.data: {}".format(pformat(instance.data)))
