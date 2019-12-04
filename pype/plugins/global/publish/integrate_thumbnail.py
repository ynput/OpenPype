import os
import sys
import errno
import shutil
import copy

import six
import pyblish.api
from bson.objectid import ObjectId

from avalon import api, dbio


class IntegrateThumbnails(pyblish.api.InstancePlugin):
    """Integrate Thumbnails."""

    label = "Integrate Thumbnails"
    order = pyblish.api.IntegratorOrder + 0.01
    families = ["review"]

    def process(self, instance):
        repre_ids = instance.get("published_representation_ids")
        if not repre_ids:
            self.log.debug(
                "There are not published representation ids on the instance."
            )
            return

        project_name = api.Session["AVALON_PROJECT"]

        anatomy = instance.context.data["anatomy"]
        if "publish" not in anatomy.templates:
            self.log.error("Anatomy does not have set publish key!")
            return

        if "thumbnail" not in anatomy.templates["publish"]:
            self.log.warning((
                "There is not set \"thumbnail\" template for project {}"
            ).format(project_name))
            return

        thumbnail_template = anatomy.templates["publish"]["thumbnail"]

        dbio.install()
        repres = dbio.find({
            "_id": {"$in": repre_ids},
            "type": "representation"
        })
        if not repres:
            self.log.debug((
                "There are not representations in database with ids {}"
            ).format(str(repre_ids)))
            return

        thumb_repre = None
        for repre in repres:
            if repre["name"].lower() == "thumbnail":
                thumb_repre = repre
                break

        if not thumb_repre:
            self.log.debug(
                "There is not representation with name \"thumbnail\""
            )
            return

        version = dbio.find_one({"_id": thumb_repre["parent"]})
        if not version:
            self.log.warning("There does not exist version with id {}".format(
                str(thumb_repre["parent"])
            ))
            return

        # Get full path to thumbnail file from representation
        src_full_path = os.path.normpath(thumb_repre["data"]["path"])
        if not os.path.exists(src_full_path):
            self.log.warning("Thumbnail file was not found. Path: {}".format(
                src_full_path
            ))
            return

        # Create id for mongo entity now to fill anatomy template
        thumbnail_id = ObjectId()

        # Prepare anatomy template fill data
        template_data = copy.deepcopy(thumb_repre["context"])
        template_data["_id"] = str(thumbnail_id)
        template_data["thumbnail_root"] = os.environ.get(
            "AVALON_THUMBNAIL_ROOT"
        )

        anatomy_filled = anatomy.format(template_data)
        final_path = anatomy_filled.get("publish", {}).get("thumbnail")
        if not final_path:
            self.log.warning((
                "Anatomy template was not filled with entered data"
                "\nTemplate: {} "
                "\nData: {}"
            ).format(thumbnail_template, str(template_data)))
            return

        dst_full_path = os.path.normpath(final_path)
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

        thumbnail_entity = {
            "_id": thumbnail_id,
            "type": "thumbnail",
            "schema": "pype:thumbnail-1.0",
            "data": {
                "template": thumbnail_template,
                "template_data": template_data
            }
        }
        # Create thumbnail entity
        dbio.insert_one(thumbnail_entity)
        self.log.debug(
            "Creating entity in database {}".format(str(thumbnail_entity))
        )
        # Set thumbnail id for version
        dbio.update_one(
            {"_id": version["_id"]},
            {"$set": {"data.thumbnail_id": thumbnail_id}}
        )
        self.log.debug("Setting thumbnail for version \"{}\" <{}>".format(
            version["name"], str(version["_id"])
        ))
