import os
import collections
from pprint import pformat

import pyblish.api

from openpype.pipeline import legacy_io


class AppendCelactionAudio(pyblish.api.ContextPlugin):

    label = "Colect Audio for publishing"
    order = pyblish.api.CollectorOrder + 0.1

    def process(self, context):
        self.log.info('Collecting Audio Data')
        asset_doc = context.data["assetEntity"]

        # get all available representations
        subsets = self.get_subsets(
            asset_doc,
            representations=["audio", "wav"]
        )
        self.log.info(f"subsets is: {pformat(subsets)}")

        if not subsets.get("audioMain"):
            raise AttributeError("`audioMain` subset does not exist")

        reprs = subsets.get("audioMain", {}).get("representations", [])
        self.log.info(f"reprs is: {pformat(reprs)}")

        repr = next((r for r in reprs), None)
        if not repr:
            raise "Missing `audioMain` representation"
        self.log.info(f"representation is: {repr}")

        audio_file = repr.get('data', {}).get('path', "")

        if os.path.exists(audio_file):
            context.data["audioFile"] = audio_file
            self.log.info(
                'audio_file: {}, has been added to context'.format(audio_file))
        else:
            self.log.warning("Couldn't find any audio file on Ftrack.")

    def get_subsets(self, asset_doc, representations):
        """
        Query subsets with filter on name.

        The method will return all found subsets and its defined version
        and subsets. Version could be specified with number. Representation
        can be filtered.

        Arguments:
            asset_doct (dict): Asset (shot) mongo document
            representations (list): list for all representations

        Returns:
            dict: subsets with version and representations in keys
        """

        # Query all subsets for asset
        subset_docs = legacy_io.find({
            "type": "subset",
            "parent": asset_doc["_id"]
        })
        # Collect all subset ids
        subset_ids = [
            subset_doc["_id"]
            for subset_doc in subset_docs
        ]

        # Check if we found anything
        assert subset_ids, (
            "No subsets found. Check correct filter. "
            "Try this for start `r'.*'`: asset: `{}`"
        ).format(asset_doc["name"])

        # Last version aggregation
        pipeline = [
            # Find all versions of those subsets
            {"$match": {
                "type": "version",
                "parent": {"$in": subset_ids}
            }},
            # Sorting versions all together
            {"$sort": {"name": 1}},
            # Group them by "parent", but only take the last
            {"$group": {
                "_id": "$parent",
                "_version_id": {"$last": "$_id"},
                "name": {"$last": "$name"}
            }}
        ]
        last_versions_by_subset_id = dict()
        for doc in legacy_io.aggregate(pipeline):
            doc["parent"] = doc["_id"]
            doc["_id"] = doc.pop("_version_id")
            last_versions_by_subset_id[doc["parent"]] = doc

        version_docs_by_id = {}
        for version_doc in last_versions_by_subset_id.values():
            version_docs_by_id[version_doc["_id"]] = version_doc

        repre_docs = legacy_io.find({
            "type": "representation",
            "parent": {"$in": list(version_docs_by_id.keys())},
            "name": {"$in": representations}
        })
        repre_docs_by_version_id = collections.defaultdict(list)
        for repre_doc in repre_docs:
            version_id = repre_doc["parent"]
            repre_docs_by_version_id[version_id].append(repre_doc)

        output_dict = {}
        for version_id, repre_docs in repre_docs_by_version_id.items():
            version_doc = version_docs_by_id[version_id]
            subset_id = version_doc["parent"]
            subset_doc = last_versions_by_subset_id[subset_id]
            # Store queried docs by subset name
            output_dict[subset_doc["name"]] = {
                "representations": repre_docs,
                "version": version_doc
            }

        return output_dict
