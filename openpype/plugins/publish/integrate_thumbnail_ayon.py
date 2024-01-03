""" Integrate Thumbnails for Openpype use in Loaders.

    This thumbnail is different from 'thumbnail' representation which could
    be uploaded to Ftrack, or used as any other representation in Loaders to
    pull into a scene.

    This one is used only as image describing content of published item and
        shows up only in Loader or WebUI.

    Instance must have 'published_representations' to
        be able to integrate thumbnail.
    Possible sources of thumbnail paths:
    - instance.data["thumbnailPath"]
    - representation with 'thumbnail' name in 'published_representations'
    - context.data["thumbnailPath"]

    Notes:
        Issue with 'thumbnail' representation is that we most likely don't
            want to integrate it as representation. Integrated representation
            is polluting Loader and database without real usage. That's why
            they usually have 'delete' tag to skip the integration.

"""

import os
import collections

import pyblish.api

from openpype import AYON_SERVER_ENABLED
from openpype.client import get_versions
from openpype.client.operations import OperationsSession

InstanceFilterResult = collections.namedtuple(
    "InstanceFilterResult",
    ["instance", "thumbnail_path", "version_id"]
)


class IntegrateThumbnailsAYON(pyblish.api.ContextPlugin):
    """Integrate Thumbnails for Openpype use in Loaders."""

    label = "Integrate Thumbnails to AYON"
    order = pyblish.api.IntegratorOrder + 0.01

    required_context_keys = [
        "project", "asset", "task", "subset", "version"
    ]

    def process(self, context):
        if not AYON_SERVER_ENABLED:
            self.log.debug("AYON is not enabled. Skipping")
            return

        # Filter instances which can be used for integration
        filtered_instance_items = self._prepare_instances(context)
        if not filtered_instance_items:
            self.log.debug(
                "All instances were filtered. Thumbnail integration skipped."
            )
            return

        project_name = context.data["projectName"]

        # Collect version ids from all filtered instance
        version_ids = {
            instance_items.version_id
            for instance_items in filtered_instance_items
        }
        # Query versions
        version_docs = get_versions(
            project_name,
            version_ids=version_ids,
            hero=True,
            fields=["_id", "type", "name"]
        )
        # Store version by their id (converted to string)
        version_docs_by_str_id = {
            str(version_doc["_id"]): version_doc
            for version_doc in version_docs
        }
        self._integrate_thumbnails(
            filtered_instance_items,
            version_docs_by_str_id,
            project_name
        )

    def _prepare_instances(self, context):
        context_thumbnail_path = context.data.get("thumbnailPath")
        valid_context_thumbnail = bool(
            context_thumbnail_path
            and os.path.exists(context_thumbnail_path)
        )

        filtered_instances = []
        for instance in context:
            instance_label = self._get_instance_label(instance)
            # Skip instances without published representations
            # - there is no place where to put the thumbnail
            published_repres = instance.data.get("published_representations")
            if not published_repres:
                self.log.debug((
                    "There are no published representations"
                    " on the instance {}."
                ).format(instance_label))
                continue

            # Find thumbnail path on instance
            thumbnail_path = (
                instance.data.get("thumbnailPath")
                or self._get_instance_thumbnail_path(published_repres)
            )
            if thumbnail_path:
                self.log.debug((
                    "Found thumbnail path for instance \"{}\"."
                    " Thumbnail path: {}"
                ).format(instance_label, thumbnail_path))

            elif valid_context_thumbnail:
                # Use context thumbnail path if is available
                thumbnail_path = context_thumbnail_path
                self.log.debug((
                    "Using context thumbnail path for instance \"{}\"."
                    " Thumbnail path: {}"
                ).format(instance_label, thumbnail_path))

            # Skip instance if thumbnail path is not available for it
            if not thumbnail_path:
                self.log.debug((
                    "Skipping thumbnail integration for instance \"{}\"."
                    " Instance and context"
                    " thumbnail paths are not available."
                ).format(instance_label))
                continue

            version_id = str(self._get_version_id(published_repres))
            filtered_instances.append(
                InstanceFilterResult(instance, thumbnail_path, version_id)
            )
        return filtered_instances

    def _get_version_id(self, published_representations):
        for repre_info in published_representations.values():
            return repre_info["representation"]["parent"]

    def _get_instance_thumbnail_path(self, published_representations):
        thumb_repre_doc = None
        for repre_info in published_representations.values():
            repre_doc = repre_info["representation"]
            if "thumbnail" in repre_doc["name"].lower():
                thumb_repre_doc = repre_doc
                break

        if thumb_repre_doc is None:
            self.log.debug(
                "There is no representation with name \"thumbnail\""
            )
            return None

        path = thumb_repre_doc["data"]["path"]
        if not os.path.exists(path):
            self.log.warning(
                "Thumbnail file cannot be found. Path: {}".format(path)
            )
            return None
        return os.path.normpath(path)

    def _integrate_thumbnails(
        self,
        filtered_instance_items,
        version_docs_by_str_id,
        project_name
    ):
        from openpype.client.server.operations import create_thumbnail

        # Make sure each entity id has defined only one thumbnail id
        thumbnail_info_by_entity_id = {}
        for instance_item in filtered_instance_items:
            instance, thumbnail_path, version_id = instance_item
            instance_label = self._get_instance_label(instance)
            version_doc = version_docs_by_str_id.get(version_id)
            if not version_doc:
                self.log.warning((
                    "Version entity for instance \"{}\" was not found."
                ).format(instance_label))
                continue

            thumbnail_id = create_thumbnail(project_name, thumbnail_path)

            # Set thumbnail id for version
            thumbnail_info_by_entity_id[version_id] = {
                "thumbnail_id": thumbnail_id,
                "entity_type": version_doc["type"],
            }
            if version_doc["type"] == "hero_version":
                version_name = "Hero"
            else:
                version_name = version_doc["name"]
            self.log.debug("Setting thumbnail for version \"{}\" <{}>".format(
                version_name, version_id
            ))

            asset_entity = instance.data["assetEntity"]
            thumbnail_info_by_entity_id[asset_entity["_id"]] = {
                "thumbnail_id": thumbnail_id,
                "entity_type": "asset",
            }
            self.log.debug("Setting thumbnail for asset \"{}\" <{}>".format(
                asset_entity["name"], version_id
            ))

        op_session = OperationsSession()
        for entity_id, thumbnail_info in thumbnail_info_by_entity_id.items():
            thumbnail_id = thumbnail_info["thumbnail_id"]
            op_session.update_entity(
                project_name,
                thumbnail_info["entity_type"],
                entity_id,
                {"data.thumbnail_id": thumbnail_id}
            )
        op_session.commit()

    def _get_instance_label(self, instance):
        return (
            instance.data.get("label")
            or instance.data.get("name")
            or "N/A"
        )
