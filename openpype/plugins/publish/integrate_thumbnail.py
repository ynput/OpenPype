""" Integrate Thumbnails for Openpype use in Loaders.

    This thumbnail is different from 'thumbnail' representation which could
    be uploaded to Ftrack, or used as any other representation in Loaders to
    pull into a scene.

    This one is used only as image describing content of published item and
    shows up only in Loader in right column section.
"""

import os
import sys
import errno
import shutil
import copy
import collections

import six
import pyblish.api

from openpype.client import get_versions
from openpype.client.operations import OperationsSession, new_thumbnail_doc

InstanceFilterResult = collections.namedtuple(
    "InstanceFilterResult",
    ["instance", "thumbnail_path", "version_id"]
)


class IntegrateThumbnails(pyblish.api.ContextPlugin):
    """Integrate Thumbnails for Openpype use in Loaders."""

    label = "Integrate Thumbnails"
    order = pyblish.api.IntegratorOrder + 0.01

    required_context_keys = [
        "project", "asset", "task", "subset", "version"
    ]

    def process(self, context):
        # Filter instances which can be used for integration
        filtered_instance_items = self._prepare_instances(context)
        if not filtered_instance_items:
            self.log.info(
                "All instances were filtered. Thumbnail integration skipped."
            )
            return

        # Initial validation of available templated and required keys
        env_key = "AVALON_THUMBNAIL_ROOT"
        thumbnail_root_format_key = "{thumbnail_root}"
        thumbnail_root = os.environ.get(env_key) or ""

        anatomy = context.data["anatomy"]
        project_name = anatomy.project_name
        if "publish" not in anatomy.templates:
            self.log.warning(
                "Anatomy is missing the \"publish\" key. Skipping."
            )
            return

        if "thumbnail" not in anatomy.templates["publish"]:
            self.log.warning((
                "There is no \"thumbnail\" template set for the project"
                " \"{}\". Skipping."
            ).format(project_name))
            return

        thumbnail_template = anatomy.templates["publish"]["thumbnail"]
        if not thumbnail_template:
            self.log.info("Thumbnail template is not filled. Skipping.")
            return

        if (
            not thumbnail_root
            and thumbnail_root_format_key in thumbnail_template
        ):
            self.log.warning(("{} is not set. Skipping.").format(env_key))
            return

        # Collect verion ids from all filtered instance
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
            anatomy,
            thumbnail_root
        )

    def _prepare_instances(self, context):
        context_thumbnail_path = context.get("thumbnailPath")
        valid_context_thumbnail = False
        if context_thumbnail_path and os.path.exists(context_thumbnail_path):
            valid_context_thumbnail = True

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
            thumbnail_path = self._get_instance_thumbnail_path(
                published_repres)
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
                self.log.info((
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
            if repre_doc["name"].lower() == "thumbnail":
                thumb_repre_doc = repre_doc
                break

        if thumb_repre_doc is None:
            self.log.debug(
                "There is not representation with name \"thumbnail\""
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
        anatomy,
        thumbnail_root
    ):
        op_session = OperationsSession()
        project_name = anatomy.project_name

        for instance_item in filtered_instance_items:
            instance, thumbnail_path, version_id = instance_item
            instance_label = self._get_instance_label(instance)
            version_doc = version_docs_by_str_id.get(version_id)
            if not version_doc:
                self.log.warning((
                    "Version entity for instance \"{}\" was not found."
                ).format(instance_label))
                continue

            filename, file_extension = os.path.splitext(thumbnail_path)
            # Create id for mongo entity now to fill anatomy template
            thumbnail_doc = new_thumbnail_doc()
            thumbnail_id = thumbnail_doc["_id"]

            # Prepare anatomy template fill data
            template_data = copy.deepcopy(instance.data["anatomyData"])
            template_data.update({
                "_id": str(thumbnail_id),
                "ext": file_extension[1:],
                "name": "thumbnail",
                "thumbnail_root": thumbnail_root,
                "thumbnail_type": "thumbnail"
            })

            anatomy_filled = anatomy.format(template_data)
            thumbnail_template = anatomy.templates["publish"]["thumbnail"]
            template_filled = anatomy_filled["publish"]["thumbnail"]

            dst_full_path = os.path.normpath(str(template_filled))
            self.log.debug("Copying file .. {} -> {}".format(
                thumbnail_path, dst_full_path
            ))
            dirname = os.path.dirname(dst_full_path)
            try:
                os.makedirs(dirname)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    tp, value, tb = sys.exc_info()
                    six.reraise(tp, value, tb)

            shutil.copy(thumbnail_path, dst_full_path)

            # Clean template data from keys that are dynamic
            for key in ("_id", "thumbnail_root"):
                template_data.pop(key, None)

            repre_context = template_filled.used_values
            for key in self.required_context_keys:
                value = template_data.get(key)
                if not value:
                    continue
                repre_context[key] = template_data[key]

            thumbnail_doc["data"] = {
                "template": thumbnail_template,
                "template_data": repre_context
            }
            op_session.create_entity(
                project_name, thumbnail_doc["type"], thumbnail_doc
            )
            # Create thumbnail entity
            self.log.debug(
                "Creating entity in database {}".format(str(thumbnail_doc))
            )

            # Set thumbnail id for version
            op_session.update_entity(
                project_name,
                version_doc["type"],
                version_doc["_id"],
                {"data.thumbnail_id": thumbnail_id}
            )
            if version_doc["type"] == "hero_version":
                version_name = "Hero"
            else:
                version_name = version_doc["name"]
            self.log.debug("Setting thumbnail for version \"{}\" <{}>".format(
                version_name, version_id
            ))

            asset_entity = instance.data["assetEntity"]
            op_session.update_entity(
                project_name,
                asset_entity["type"],
                asset_entity["_id"],
                {"data.thumbnail_id": thumbnail_id}
            )
            self.log.debug("Setting thumbnail for asset \"{}\" <{}>".format(
                asset_entity["name"], version_id
            ))

        op_session.commit()

    def _get_instance_label(self, instance):
        return (
            instance.data.get("label")
            or instance.data.get("name")
            or "N/A"
        )
