import os
import logging
import shutil

import errno
import pyblish.api
from avalon import api, io
from avalon.vendor import filelink


log = logging.getLogger(__name__)


class IntegrateMasterVersion(pyblish.api.InstancePlugin):
    label = "Integrate Master Version"
    # Must happen after IntegrateNew
    order = pyblish.api.IntegratorOrder + 0.1

    ignored_representation_names = []

    def process(self, instance):
        published_repres = instance.data.get("published_representations")
        if not published_repres:
            self.log.debug(
                "There are not published representations on the instance."
            )
            return

        project_name = api.Session["AVALON_PROJECT"]

        # TODO raise error if master not set?
        anatomy = instance.context.data["anatomy"]
        if "publish" not in anatomy.templates:
            self.warning("Anatomy does not have set publish key!")
            return

        if "master" not in anatomy.templates["publish"]:
            self.warning((
                "There is not set \"master\" template for project \"{}\""
            ).format(project_name))
            return

        version_entity = None

        filtered_repre_ids = []
        for repre_id, repre_info in published_repres.items():
            repre = repre_info["representation"]
            if version_entity is None:
                version_entity = repre_info.get("version_entity")

            if repre["name"].lower() in self.ignored_representation_names:
                filtered_repre_ids.append(repre_id)

        for repre_id in filtered_repre_ids:
            published_repres.pop(repre_id, None)

        if not published_repres:
            self.log.debug(
                "All published representations were filtered by name."
            )
            return

        if version_entity is None:
            version_entity = (
                self.version_from_representations(published_repres)
            )

        if not version_entity:
            self.log.warning("Can't find origin version in database.")
            return

        cur_master_version, cur_master_repres = (
            self.current_master_ents(version_entity)
        )

        cur_master_repres_by_name = {
            repre["name"].lower(): repre for repre in cur_master_repres
        }

        if cur_master_version:
            cur_master_version_id = cur_master_version["_id"]
        else:
            cur_master_version_id = io.ObjectId()

        new_master_version = {
            "_id": cur_master_version_id,
            "version_id": version_entity["_id"],
            "parent": version_entity["parent"],
            "type": "master_version",
            "schema": "pype:master_version-1.0"
        }

        repres_to_replace = {}
        for repre_id, repre_info in published_repres.items():
            repre = repre_info["representation"]
            repre_name_low = repre["name"].lower()
            if repre_name_low in cur_master_repres_by_name:
                repres_to_replace[repre_id] = (
                    cur_master_repres_by_name.pop(repre_name_low)
                )

        if cur_master_version:
            io.replace_one(
                {"_id": new_master_version["_id"]},
                new_master_version
            )
        else:
            io.insert_one(new_master_version)

    def version_from_representations(self, repres):
        for repre in repres:
            version = io.find_one({"_id": repre["parent"]})
            if version:
                return version

    def current_master_ents(self, version):
        master_version = io.find_one({
            "parent": version["parent"],
            "type": "master_version"
        })

        if not master_version:
            return (None, [])

        master_repres = list(io.find({
            "parent": master_version["_id"],
            "type": "representation"
        }))
        return (master_version, master_repres)
