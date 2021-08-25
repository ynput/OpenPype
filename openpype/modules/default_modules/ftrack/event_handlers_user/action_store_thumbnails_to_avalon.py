import os
import errno
import json
import requests

from bson.objectid import ObjectId
from openpype_modules.ftrack.lib import BaseAction, statics_icon
from openpype.api import Anatomy
from avalon.api import AvalonMongoDB

from openpype_modules.ftrack.lib.avalon_sync import CUST_ATTR_ID_KEY


class StoreThumbnailsToAvalon(BaseAction):
    # Action identifier
    identifier = "store.thubmnail.to.avalon"
    # Action label
    label = "OpenPype Admin"
    # Action variant
    variant = "- Store Thumbnails to avalon"
    # Action description
    description = 'Test action'
    # roles that are allowed to register this action
    icon = statics_icon("ftrack", "action_icons", "OpenPypeAdmin.svg")
    settings_key = "store_thubmnail_to_avalon"

    thumbnail_key = "AVALON_THUMBNAIL_ROOT"

    def __init__(self, *args, **kwargs):
        self.db_con = AvalonMongoDB()
        super(StoreThumbnailsToAvalon, self).__init__(*args, **kwargs)

    def discover(self, session, entities, event):
        is_valid = False
        for entity in entities:
            if entity.entity_type.lower() == "assetversion":
                is_valid = True
                break

        if is_valid:
            is_valid = self.valid_roles(session, entities, event)
        return is_valid

    def launch(self, session, entities, event):
        user = session.query(
            "User where username is '{0}'".format(session.api_user)
        ).one()
        action_job = session.create("Job", {
            "user": user,
            "status": "running",
            "data": json.dumps({
                "description": "Storing thumbnails to avalon."
            })
        })
        session.commit()

        project = self.get_project_from_entity(entities[0])
        project_name = project["full_name"]
        anatomy = Anatomy(project_name)

        if "publish" not in anatomy.templates:
            msg = "Anatomy does not have set publish key!"

            action_job["status"] = "failed"
            session.commit()

            self.log.warning(msg)

            return {
                "success": False,
                "message": msg
            }

        if "thumbnail" not in anatomy.templates["publish"]:
            msg = (
                "There is not set \"thumbnail\""
                " template in Antomy for project \"{}\""
            ).format(project_name)

            action_job["status"] = "failed"
            session.commit()

            self.log.warning(msg)

            return {
                "success": False,
                "message": msg
            }

        thumbnail_roots = os.environ.get(self.thumbnail_key)
        if (
            "{thumbnail_root}" in anatomy.templates["publish"]["thumbnail"]
            and not thumbnail_roots
        ):
            msg = "`{}` environment is not set".format(self.thumbnail_key)

            action_job["status"] = "failed"
            session.commit()

            self.log.warning(msg)

            return {
                "success": False,
                "message": msg
            }

        existing_thumbnail_root = None
        for path in thumbnail_roots.split(os.pathsep):
            if os.path.exists(path):
                existing_thumbnail_root = path
                break

        if existing_thumbnail_root is None:
            msg = (
                "Can't access paths, set in `{}` ({})"
            ).format(self.thumbnail_key, thumbnail_roots)

            action_job["status"] = "failed"
            session.commit()

            self.log.warning(msg)

            return {
                "success": False,
                "message": msg
            }

        example_template_data = {
            "_id": "ID",
            "thumbnail_root": "THUBMNAIL_ROOT",
            "thumbnail_type": "THUMBNAIL_TYPE",
            "ext": ".EXT",
            "project": {
                "name": "PROJECT_NAME",
                "code": "PROJECT_CODE"
            },
            "asset": "ASSET_NAME",
            "subset": "SUBSET_NAME",
            "version": "VERSION_NAME",
            "hierarchy": "HIERARCHY"
        }
        tmp_filled = anatomy.format_all(example_template_data)
        thumbnail_result = tmp_filled["publish"]["thumbnail"]
        if not thumbnail_result.solved:
            missing_keys = thumbnail_result.missing_keys
            invalid_types = thumbnail_result.invalid_types
            submsg = ""
            if missing_keys:
                submsg += "Missing keys: {}".format(", ".join(
                    ["\"{}\"".format(key) for key in missing_keys]
                ))

            if invalid_types:
                items = []
                for key, value in invalid_types.items():
                    items.append("{}{}".format(str(key), str(value)))
                submsg += "Invalid types: {}".format(", ".join(items))

            msg = (
                "Thumbnail Anatomy template expects more keys than action"
                " can offer. {}"
            ).format(submsg)

            action_job["status"] = "failed"
            session.commit()

            self.log.warning(msg)

            return {
                "success": False,
                "message": msg
            }

        thumbnail_template = anatomy.templates["publish"]["thumbnail"]

        self.db_con.install()

        for entity in entities:
            # Skip if entity is not AssetVersion (never should happend, but..)
            if entity.entity_type.lower() != "assetversion":
                continue

            # Skip if AssetVersion don't have thumbnail
            thumbnail_ent = entity["thumbnail"]
            if thumbnail_ent is None:
                self.log.debug((
                    "Skipping. AssetVersion don't "
                    "have set thumbnail. {}"
                ).format(entity["id"]))
                continue

            avalon_ents_result = self.get_avalon_entities_for_assetversion(
                entity, self.db_con
            )
            version_full_path = (
                "Asset: \"{project_name}/{asset_path}\""
                " | Subset: \"{subset_name}\""
                " | Version: \"{version_name}\""
            ).format(**avalon_ents_result)

            version = avalon_ents_result["version"]
            if not version:
                self.log.warning((
                    "AssetVersion does not have version in avalon. {}"
                ).format(version_full_path))
                continue

            thumbnail_id = version["data"].get("thumbnail_id")
            if thumbnail_id:
                self.log.info((
                    "AssetVersion skipped, already has thubmanil set. {}"
                ).format(version_full_path))
                continue

            # Get thumbnail extension
            file_ext = thumbnail_ent["file_type"]
            if not file_ext.startswith("."):
                file_ext = ".{}".format(file_ext)

            avalon_project = avalon_ents_result["project"]
            avalon_asset = avalon_ents_result["asset"]
            hierarchy = ""
            parents = avalon_asset["data"].get("parents") or []
            if parents:
                hierarchy = "/".join(parents)

            # Prepare anatomy template fill data
            # 1. Create new id for thumbnail entity
            thumbnail_id = ObjectId()

            template_data = {
                "_id": str(thumbnail_id),
                "thumbnail_root": existing_thumbnail_root,
                "thumbnail_type": "thumbnail",
                "ext": file_ext,
                "project": {
                    "name": avalon_project["name"],
                    "code": avalon_project["data"].get("code")
                },
                "asset": avalon_ents_result["asset_name"],
                "subset": avalon_ents_result["subset_name"],
                "version": avalon_ents_result["version_name"],
                "hierarchy": hierarchy
            }

            anatomy_filled = anatomy.format(template_data)
            thumbnail_path = anatomy_filled["publish"]["thumbnail"]
            thumbnail_path = thumbnail_path.replace("..", ".")
            thumbnail_path = os.path.normpath(thumbnail_path)

            downloaded = False
            for loc in (thumbnail_ent.get("component_locations") or []):
                res_id = loc.get("resource_identifier")
                if not res_id:
                    continue

                thubmnail_url = self.get_thumbnail_url(res_id)
                if self.download_file(thubmnail_url, thumbnail_path):
                    downloaded = True
                    break

            if not downloaded:
                self.log.warning(
                    "Could not download thumbnail for {}".format(
                        version_full_path
                    )
                )
                continue

            # Clean template data from keys that are dynamic
            template_data.pop("_id")
            template_data.pop("thumbnail_root")

            thumbnail_entity = {
                "_id": thumbnail_id,
                "type": "thumbnail",
                "schema": "openpype:thumbnail-1.0",
                "data": {
                    "template": thumbnail_template,
                    "template_data": template_data
                }
            }

            # Create thumbnail entity
            self.db_con.insert_one(thumbnail_entity)
            self.log.debug(
                "Creating entity in database {}".format(str(thumbnail_entity))
            )

            # Set thumbnail id for version
            self.db_con.update_one(
                {"_id": version["_id"]},
                {"$set": {"data.thumbnail_id": thumbnail_id}}
            )

            self.db_con.update_one(
                {"_id": avalon_asset["_id"]},
                {"$set": {"data.thumbnail_id": thumbnail_id}}
            )

        action_job["status"] = "done"
        session.commit()

        return True

    def get_thumbnail_url(self, resource_identifier, size=None):
        # TODO use ftrack_api method rather (find way how to use it)
        url_string = (
            u'{url}/component/thumbnail?id={id}&username={username}'
            u'&apiKey={apiKey}'
        )
        url = url_string.format(
            url=self.session.server_url,
            id=resource_identifier,
            username=self.session.api_user,
            apiKey=self.session.api_key
        )
        if size:
            url += u'&size={0}'.format(size)

        return url

    def download_file(self, source_url, dst_file_path):
        dir_path = os.path.dirname(dst_file_path)
        try:
            os.makedirs(dir_path)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                self.log.warning(
                    "Could not create folder: \"{}\"".format(dir_path)
                )
                return False

        self.log.debug(
            "Downloading file \"{}\" -> \"{}\"".format(
                source_url, dst_file_path
            )
        )
        file_open = open(dst_file_path, "wb")
        try:
            file_open.write(requests.get(source_url).content)
        except Exception:
            self.log.warning(
                "Download of image `{}` failed.".format(source_url)
            )
            return False
        finally:
            file_open.close()
        return True

    def get_avalon_entities_for_assetversion(self, asset_version, db_con):
        output = {
            "success": True,
            "message": None,
            "project": None,
            "project_name": None,
            "asset": None,
            "asset_name": None,
            "asset_path": None,
            "subset": None,
            "subset_name": None,
            "version": None,
            "version_name": None,
            "representations": None
        }

        db_con.install()

        ft_asset = asset_version["asset"]
        subset_name = ft_asset["name"]
        version = asset_version["version"]
        parent = ft_asset["parent"]
        ent_path = "/".join(
            [ent["name"] for ent in parent["link"]]
        )
        project = self.get_project_from_entity(asset_version)
        project_name = project["full_name"]

        output["project_name"] = project_name
        output["asset_name"] = parent["name"]
        output["asset_path"] = ent_path
        output["subset_name"] = subset_name
        output["version_name"] = version

        db_con.Session["AVALON_PROJECT"] = project_name

        avalon_project = db_con.find_one({"type": "project"})
        output["project"] = avalon_project

        if not avalon_project:
            output["success"] = False
            output["message"] = (
                "Project not synchronized to avalon `{}`".format(project_name)
            )
            return output

        asset_ent = None
        asset_mongo_id = parent["custom_attributes"].get(CUST_ATTR_ID_KEY)
        if asset_mongo_id:
            try:
                asset_mongo_id = ObjectId(asset_mongo_id)
                asset_ent = db_con.find_one({
                    "type": "asset",
                    "_id": asset_mongo_id
                })
            except Exception:
                pass

        if not asset_ent:
            asset_ent = db_con.find_one({
                "type": "asset",
                "data.ftrackId": parent["id"]
            })

        output["asset"] = asset_ent

        if not asset_ent:
            output["success"] = False
            output["message"] = (
                "Not synchronized entity to avalon `{}`".format(ent_path)
            )
            return output

        asset_mongo_id = asset_ent["_id"]

        subset_ent = db_con.find_one({
            "type": "subset",
            "parent": asset_mongo_id,
            "name": subset_name
        })

        output["subset"] = subset_ent

        if not subset_ent:
            output["success"] = False
            output["message"] = (
                "Subset `{}` does not exist under Asset `{}`"
            ).format(subset_name, ent_path)
            return output

        version_ent = db_con.find_one({
            "type": "version",
            "name": version,
            "parent": subset_ent["_id"]
        })

        output["version"] = version_ent

        if not version_ent:
            output["success"] = False
            output["message"] = (
                "Version `{}` does not exist under Subset `{}` | Asset `{}`"
            ).format(version, subset_name, ent_path)
            return output

        repre_ents = list(db_con.find({
            "type": "representation",
            "parent": version_ent["_id"]
        }))

        output["representations"] = repre_ents
        return output


def register(session):
    StoreThumbnailsToAvalon(session).register()
