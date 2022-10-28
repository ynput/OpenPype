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

import six
import pyblish.api

from openpype.client import get_version_by_id
from openpype.client.operations import OperationsSession, new_thumbnail_doc


class IntegrateThumbnails(pyblish.api.InstancePlugin):
    """Integrate Thumbnails for Openpype use in Loaders."""

    label = "Integrate Thumbnails"
    order = pyblish.api.IntegratorOrder + 0.01
    families = ["review"]

    required_context_keys = [
        "project", "asset", "task", "subset", "version"
    ]

    def process(self, instance):
        context_thumbnail_path = instance.context.get("thumbnailPath")

        env_key = "AVALON_THUMBNAIL_ROOT"
        thumbnail_root_format_key = "{thumbnail_root}"
        thumbnail_root = os.environ.get(env_key) or ""

        published_repres = instance.data.get("published_representations")
        if not published_repres:
            self.log.debug(
                "There are no published representations on the instance."
            )
            return

        anatomy = instance.context.data["anatomy"]
        project_name = anatomy.project_name
        if "publish" not in anatomy.templates:
            self.log.warning("Anatomy is missing the \"publish\" key!")
            return

        if "thumbnail" not in anatomy.templates["publish"]:
            self.log.warning((
                "There is no \"thumbnail\" template set for the project \"{}\""
            ).format(project_name))
            return

        thumbnail_template = anatomy.templates["publish"]["thumbnail"]
        if (
            not thumbnail_root
            and thumbnail_root_format_key in thumbnail_template
        ):
            self.log.warning((
                "{} is not set. Skipping thumbnail integration."
            ).format(env_key))
            return

        version_id = None
        thumb_repre = None
        thumb_repre_anatomy_data = None
        for repre_info in published_repres.values():
            repre = repre_info["representation"]
            if version_id is None:
                version_id = repre["parent"]

            if repre["name"].lower() == "thumbnail":
                thumb_repre = repre
                thumb_repre_anatomy_data = repre_info["anatomy_data"]
                break

        # Use context thumbnail (if is available)
        if not thumb_repre:
            self.log.debug(
                "There is not representation with name \"thumbnail\""
            )
            src_full_path = context_thumbnail_path
        else:
            # Get full path to thumbnail file from representation
            src_full_path = os.path.normpath(thumb_repre["data"]["path"])

        if not os.path.exists(src_full_path):
            self.log.warning("Thumbnail file was not found. Path: {}".format(
                src_full_path
            ))
            return

        version = get_version_by_id(project_name, version_id)
        if not version:
            raise AssertionError(
                "There does not exist version with id {}".format(
                    str(version_id)
                )
            )

        filename, file_extension = os.path.splitext(src_full_path)
        # Create id for mongo entity now to fill anatomy template
        thumbnail_doc = new_thumbnail_doc()
        thumbnail_id = thumbnail_doc["_id"]

        # Prepare anatomy template fill data
        template_data = copy.deepcopy(thumb_repre_anatomy_data)
        template_data.update({
            "_id": str(thumbnail_id),
            "ext": file_extension[1:],
            "thumbnail_root": thumbnail_root,
            "thumbnail_type": "thumbnail"
        })

        anatomy_filled = anatomy.format(template_data)
        template_filled = anatomy_filled["publish"]["thumbnail"]

        dst_full_path = os.path.normpath(str(template_filled))
        self.log.debug(
            "Copying file .. {} -> {}".format(src_full_path, dst_full_path)
        )
        dirname = os.path.dirname(dst_full_path)
        try:
            os.makedirs(dirname)
        except OSError as e:
            if e.errno != errno.EEXIST:
                tp, value, tb = sys.exc_info()
                six.reraise(tp, value, tb)

        shutil.copy(src_full_path, dst_full_path)

        # Clean template data from keys that are dynamic
        for key in ("_id", "thumbnail_root"):
            template_data.pop(key, None)

        repre_context = template_filled.used_values
        for key in self.required_context_keys:
            value = template_data.get(key)
            if not value:
                continue
            repre_context[key] = template_data[key]

        op_session = OperationsSession()

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
            version["type"],
            version["_id"],
            {"data.thumbnail_id": thumbnail_id}
        )
        self.log.debug("Setting thumbnail for version \"{}\" <{}>".format(
            version["name"], str(version["_id"])
        ))

        asset_entity = instance.data["assetEntity"]
        op_session.update_entity(
            project_name,
            asset_entity["type"],
            asset_entity["_id"],
            {"data.thumbnail_id": thumbnail_id}
        )
        self.log.debug("Setting thumbnail for asset \"{}\" <{}>".format(
            asset_entity["name"], str(version["_id"])
        ))

        op_session.commit()
