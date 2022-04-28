import os
import re
import collections
import pyblish.api
from pprint import pformat

from openpype.pipeline import legacy_io


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
        source_filename = self.get_source_filename(instance)
        self.log.info("Looking for asset document for file \"{}\"".format(
            source_filename
        ))
        asset_name = os.path.splitext(source_filename)[0].lower()

        asset_docs_by_name = self.selection_children_by_name(instance)

        version_number = None
        # Always first check if source filename is in assets
        matching_asset_doc = asset_docs_by_name.get(asset_name)
        if matching_asset_doc is None:
            # Check if source file contain version in name
            self.log.debug((
                "Asset doc by \"{}\" was not found trying version regex."
            ).format(asset_name))
            regex_result = self.version_regex.findall(asset_name)
            if regex_result:
                _asset_name, _version_number = regex_result[0]
                matching_asset_doc = asset_docs_by_name.get(_asset_name)
                if matching_asset_doc:
                    version_number = int(_version_number)

        if matching_asset_doc is None:
            for asset_name_low, asset_doc in asset_docs_by_name.items():
                if asset_name_low in asset_name:
                    matching_asset_doc = asset_doc
                    break

        if not matching_asset_doc:
            self.log.debug("Available asset names {}".format(
                str(list(asset_docs_by_name.keys()))
            ))
            # TODO better error message
            raise AssertionError((
                "Filename \"{}\" does not match"
                " any name of asset documents in database for your selection."
            ).format(source_filename))

        instance.data["asset"] = matching_asset_doc["name"]
        instance.data["assetEntity"] = matching_asset_doc
        if version_number is not None:
            instance.data["version"] = version_number

        self.log.info(
            f"Matching asset found: {pformat(matching_asset_doc)}"
        )

    def get_source_filename(self, instance):
        if instance.data["family"] == "background_batch":
            return os.path.basename(instance.data["source"])

        if len(instance.data["representations"]) != 1:
            raise ValueError((
                "Implementation bug: Instance data contain"
                " more than one representation."
            ))

        repre = instance.data["representations"][0]
        repre_files = repre["files"]
        if not isinstance(repre_files, str):
            raise ValueError((
                "Implementation bug: Instance's representation contain"
                " unexpected value (expected single file). {}"
            ).format(str(repre_files)))
        return repre_files

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
        for asset_doc in legacy_io.find({"type": "asset"}):
            parent_id = asset_doc["data"]["visualParent"]
            asset_docs_by_parent_id[parent_id].append(asset_doc)
        return asset_docs_by_parent_id
