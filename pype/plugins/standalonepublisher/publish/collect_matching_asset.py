import os
import re
import collections
import pyblish.api
from avalon import io
from pprint import pformat


class CollectMatchingAssetToInstance(pyblish.api.InstancePlugin):
    """
    Collecting temp json data sent from a host context
    and path for returning json data back to hostself.
    """

    label = "Collect Matching Asset to Instance"
    order = pyblish.api.CollectorOrder - 0.05
    hosts = ["standalonepublisher"]
    families = ["background_batch", "render_mov_batch"]

    # Version regex to parse asset name and version from filename
    version_regex = re.compile(r"^(.+)_v([0-9]+)$")

    def process(self, instance):
        source_file = os.path.basename(instance.data["source"]).lower()
        self.log.info("Looking for asset document for file \"{}\"".format(
            instance.data["source"]
        ))

        asset_docs_by_name = self.selection_children_by_name(instance)

        version_number = None
        # Always first check if source filename is in assets
        matching_asset_doc = asset_docs_by_name.get(source_file)
        if matching_asset_doc is None:
            # Check if source file contain version in name
            regex_result = self.version_regex.findall(source_file)
            if regex_result:
                asset_name, _version_number = regex_result[0]
                matching_asset_doc = asset_docs_by_name.get(asset_name)
                if matching_asset_doc:
                    version_number = int(_version_number)

        if matching_asset_doc is None:
            for asset_name_low, asset_doc in asset_docs_by_name.items():
                if asset_name_low in source_file:
                    matching_asset_doc = asset_doc
                    break

        if not matching_asset_doc:
            # TODO better error message
            raise AssertionError((
                "Filename \"{}\" does not match"
                " any name of asset documents in database for your selection."
            ).format(instance.data["source"]))

        instance.data["asset"] = matching_asset_doc["name"]
        instance.data["assetEntity"] = matching_asset_doc
        if version_number is not None:
            instance.data["version"] = version_number

        self.log.info(
            f"Matching asset found: {pformat(matching_asset_doc)}"
        )

    def selection_children_by_name(self, instance):
        storing_key = "childrenDocsForSelection"

        children_docs = instance.context.data.get(storing_key)
        if children_docs is None:
            top_asset_doc = instance.context.data["assetEntity"]
            assets_by_parent_id = self._asset_docs_by_parent_id(instance)
            _children_docs = self._children_docs(
                assets_by_parent_id, top_asset_doc
            )
            children_docs = {
                children_doc["name"].lower(): children_doc
                for children_doc in _children_docs
            }
            instance.context.data[storing_key] = children_docs
        return children_docs

    def _children_docs(self, documents_by_parent_id, parent_doc):
        # Find all children in reverse order, last children is at first place.
        output = []
        children = documents_by_parent_id.get(parent_doc["_id"]) or tuple()
        for child in children:
            output.extend(
                self._children_docs(documents_by_parent_id, child)
            )
        output.append(parent_doc)
        return output

    def _asset_docs_by_parent_id(self, instance):
        # Query all assets for project and store them by parent's id to list
        asset_docs_by_parent_id = collections.defaultdict(list)
        for asset_doc in io.find({"type": "asset"}):
            parent_id = asset_doc["data"]["visualParent"]
            asset_docs_by_parent_id[parent_id].append(asset_doc)
        return asset_docs_by_parent_id
