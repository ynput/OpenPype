import collections
import pyblish.api

from openpype.client import (
    get_assets,
    get_subsets,
    get_last_versions,
    get_representations,
    get_asset_name_identifier,
)
from openpype.pipeline.load import get_representation_path_with_anatomy


class CollectAudio(pyblish.api.ContextPlugin):
    """Collect asset's last published audio.

    The audio subset name searched for is defined in:
        project settings > Collect Audio

    Note:
        The plugin was instance plugin but because of so much queries the
            plugin was slowing down whole collection phase a lot thus was
            converted to context plugin which requires only 4 queries top.
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

    def process(self, context):
        # Fake filtering by family inside context plugin
        filtered_instances = []
        for instance in pyblish.api.instances_by_plugin(
            context, self.__class__
        ):
            # Skip instances that already have audio filled
            if instance.data.get("audio"):
                self.log.debug(
                    "Skipping Audio collection. It is already collected"
                )
                continue
            filtered_instances.append(instance)

        # Skip if none of instances remained
        if not filtered_instances:
            return

        # Add audio to instance if exists.
        instances_by_asset_name = collections.defaultdict(list)
        for instance in filtered_instances:
            asset_name = instance.data["asset"]
            instances_by_asset_name[asset_name].append(instance)

        asset_names = set(instances_by_asset_name.keys())
        self.log.debug((
            "Searching for audio subset '{subset}' in assets {assets}"
        ).format(
            subset=self.audio_subset_name,
            assets=", ".join([
                '"{}"'.format(asset_name)
                for asset_name in asset_names
            ])
        ))

        # Query all required documents
        project_name = context.data["projectName"]
        anatomy = context.data["anatomy"]
        repre_docs_by_asset_names = self.query_representations(
            project_name, asset_names)

        for asset_name, instances in instances_by_asset_name.items():
            repre_docs = repre_docs_by_asset_names[asset_name]
            if not repre_docs:
                continue

            repre_doc = repre_docs[0]
            repre_path = get_representation_path_with_anatomy(
                repre_doc, anatomy
            )
            for instance in instances:
                instance.data["audio"] = [{
                    "offset": 0,
                    "filename": repre_path
                }]
                self.log.debug("Audio Data added to instance ...")

    def query_representations(self, project_name, asset_names):
        """Query representations related to audio subsets for passed assets.

        Args:
            project_name (str): Project in which we're looking for all
                entities.
            asset_names (Iterable[str]): Asset names where to look for audio
                subsets and their representations.

        Returns:
            collections.defaultdict[str, List[Dict[Str, Any]]]: Representations
                related to audio subsets by asset name.
        """

        output = collections.defaultdict(list)
        # Query asset documents
        asset_docs = get_assets(
            project_name,
            asset_names=asset_names,
            fields=["_id", "name", "data.parents"]
        )

        asset_id_by_name = {
            get_asset_name_identifier(asset_doc): asset_doc["_id"]
            for asset_doc in asset_docs
        }
        asset_ids = set(asset_id_by_name.values())

        # Query subsets with name define by 'audio_subset_name' attr
        # - one or none subsets with the name should be available on an asset
        subset_docs = get_subsets(
            project_name,
            subset_names=[self.audio_subset_name],
            asset_ids=asset_ids,
            fields=["_id", "parent"]
        )
        subset_id_by_asset_id = {}
        for subset_doc in subset_docs:
            asset_id = subset_doc["parent"]
            subset_id_by_asset_id[asset_id] = subset_doc["_id"]

        subset_ids = set(subset_id_by_asset_id.values())
        if not subset_ids:
            return output

        # Find all latest versions for the subsets
        version_docs_by_subset_id = get_last_versions(
            project_name, subset_ids=subset_ids, fields=["_id", "parent"]
        )
        version_id_by_subset_id = {
            subset_id: version_doc["_id"]
            for subset_id, version_doc in version_docs_by_subset_id.items()
        }
        version_ids = set(version_id_by_subset_id.values())
        if not version_ids:
            return output

        # Find representations under latest versions of audio subsets
        repre_docs = get_representations(
            project_name, version_ids=version_ids
        )
        repre_docs_by_version_id = collections.defaultdict(list)
        for repre_doc in repre_docs:
            version_id = repre_doc["parent"]
            repre_docs_by_version_id[version_id].append(repre_doc)

        if not repre_docs_by_version_id:
            return output

        for asset_name in asset_names:
            asset_id = asset_id_by_name.get(asset_name)
            subset_id = subset_id_by_asset_id.get(asset_id)
            version_id = version_id_by_subset_id.get(subset_id)
            output[asset_name] = repre_docs_by_version_id[version_id]
        return output
