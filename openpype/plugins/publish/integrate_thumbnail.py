import os
import sys
import errno
import shutil
import copy

import six
import pyblish.api
from bson.objectid import ObjectId

from openpype.pipeline import legacy_io


class IntegrateThumbnails(pyblish.api.InstancePlugin):
    """Integrate Thumbnails."""

    label = "Integrate Thumbnails"
    order = pyblish.api.IntegratorOrder + 0.01
    families = ["review"]

    required_context_keys = [
        "project", "asset", "task", "subset", "version"
    ]

    def process(self, instance):

        if not os.environ.get("AVALON_THUMBNAIL_ROOT"):
            self.log.warning(
                "AVALON_THUMBNAIL_ROOT is not set."
                " Skipping thumbnail integration."
            )
            return

        published_repres = instance.data.get("published_representations")
        if not published_repres:
            self.log.debug(
                "There are no published representations on the instance."
            )
            return

        project_name = legacy_io.Session["AVALON_PROJECT"]

        anatomy = instance.context.data["anatomy"]
        if "publish" not in anatomy.templates:
            self.log.warning("Anatomy is missing the \"publish\" key!")
            return

        if "thumbnail" not in anatomy.templates["publish"]:
            self.log.warning((
                "There is no \"thumbnail\" template set for the project \"{}\""
            ).format(project_name))
            return

        thumb_repre = None
        thumb_repre_anatomy_data = None
        for repre_info in published_repres.values():
            repre = repre_info["representation"]
            if repre["name"].lower() == "thumbnail":
                thumb_repre = repre
                thumb_repre_anatomy_data = repre_info["anatomy_data"]
                break

        if not thumb_repre:
            self.log.debug(
                "There is not representation with name \"thumbnail\""
            )
            return

        legacy_io.install()

        thumbnail_template = anatomy.templates["publish"]["thumbnail"]

        version = legacy_io.find_one({"_id": thumb_repre["parent"]})
        if not version:
            raise AssertionError(
                "There does not exist version with id {}".format(
                    str(thumb_repre["parent"])
                )
            )

        # Get full path to thumbnail file from representation
        src_full_path = os.path.normpath(thumb_repre["data"]["path"])
        if not os.path.exists(src_full_path):
            self.log.warning("Thumbnail file was not found. Path: {}".format(
                src_full_path
            ))
            return

        filename, file_extension = os.path.splitext(src_full_path)
        # Create id for mongo entity now to fill anatomy template
        thumbnail_id = ObjectId()

        # Prepare anatomy template fill data
        template_data = copy.deepcopy(thumb_repre_anatomy_data)
        template_data.update({
            "_id": str(thumbnail_id),
            "thumbnail_root": os.environ.get("AVALON_THUMBNAIL_ROOT"),
            "ext": file_extension[1:],
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
        template_data.pop("_id")
        template_data.pop("thumbnail_root")

        repre_context = template_filled.used_values
        for key in self.required_context_keys:
            value = template_data.get(key)
            if not value:
                continue
            repre_context[key] = template_data[key]

        thumbnail_entity = {
            "_id": thumbnail_id,
            "type": "thumbnail",
            "schema": "openpype:thumbnail-1.0",
            "data": {
                "template": thumbnail_template,
                "template_data": repre_context
            }
        }
        # Create thumbnail entity
        legacy_io.insert_one(thumbnail_entity)
        self.log.debug(
            "Creating entity in database {}".format(str(thumbnail_entity))
        )
        # Set thumbnail id for version
        legacy_io.update_many(
            {"_id": version["_id"]},
            {"$set": {"data.thumbnail_id": thumbnail_id}}
        )
        self.log.debug("Setting thumbnail for version \"{}\" <{}>".format(
            version["name"], str(version["_id"])
        ))

        asset_entity = instance.data["assetEntity"]
        legacy_io.update_many(
            {"_id": asset_entity["_id"]},
            {"$set": {"data.thumbnail_id": thumbnail_id}}
        )
        self.log.debug("Setting thumbnail for asset \"{}\" <{}>".format(
            asset_entity["name"], str(version["_id"])
        ))
