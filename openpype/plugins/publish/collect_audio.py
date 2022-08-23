import pyblish.api

from openpype.client import (
    get_last_version_by_subset_name,
    get_representations,
)
from openpype.pipeline import (
    legacy_io,
    get_representation_path,
)


class CollectAudio(pyblish.api.InstancePlugin):
    """Collect asset's last published audio.

    The audio subset name searched for is defined in:
        project settings > Collect Audio
    """
    label = "Collect Asset Audio"
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
        self.log.info((
            "Searching for audio subset '{subset}'"
            " in asset '{asset}'"
        ).format(
            subset=self.audio_subset_name,
            asset=instance.data["asset"]
        ))

        repre_doc = self._get_repre_doc(instance)

        # Add audio to instance if representation was found
        if repre_doc:
            instance.data["audio"] = [{
                "offset": 0,
                "filename": get_representation_path(repre_doc)
            }]
            self.log.info("Audio Data added to instance ...")

    def _get_repre_doc(self, instance):
        cache = instance.context.data.get("__cache_asset_audio", {})
        asset_name = instance.data["asset"]

        # first try to get it from cache
        if asset_name in cache:
            return cache[asset_name]

        project_name = legacy_io.active_project()

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

        # update cache
        cache[asset_name] = repre_doc
        instance.context.data["__cache_asset_audio"].update(cache)

        return repre_doc
