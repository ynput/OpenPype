import os
import copy
import logging

from pymongo import InsertOne, ReplaceOne
import pyblish.api
from avalon import api, io, pipeline
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

        master_template = anatomy.templates["publish"]["master"]

        src_version_entity = None

        filtered_repre_ids = []
        for repre_id, repre_info in published_repres.items():
            repre = repre_info["representation"]
            if src_version_entity is None:
                src_version_entity = repre_info.get("version_entity")

            if repre["name"].lower() in self.ignored_representation_names:
                filtered_repre_ids.append(repre_id)

        for repre_id in filtered_repre_ids:
            published_repres.pop(repre_id, None)

        if not published_repres:
            self.log.debug(
                "All published representations were filtered by name."
            )
            return

        if src_version_entity is None:
            src_version_entity = (
                self.version_from_representations(published_repres)
            )

        if not src_version_entity:
            self.log.warning("Can't find origin version in database.")
            return

        old_version, old_repres = (
            self.current_master_ents(src_version_entity)
        )

        old_repres_by_name = {
            repre["name"].lower(): repre for repre in old_repres
        }

        if old_version:
            new_version_id = old_version["_id"]
        else:
            new_version_id = io.ObjectId()

        new_master_version = {
            "_id": new_version_id,
            "version_id": src_version_entity["_id"],
            "parent": src_version_entity["parent"],
            "type": "master_version",
            "schema": "pype:master_version-1.0"
        }

        bulk_writes = []

        if old_version:
            bulk_writes.append(
                ReplaceOne(
                    {"_id": new_master_version["_id"]},
                    new_master_version
                )
            )
        else:
            bulk_writes.append(
                InsertOne(new_master_version)
            )

        # Separate old representations into `to replace` and `to delete`
        old_repres_to_replace = {}
        old_repres_to_delete = {}
        for repre_id, repre_info in published_repres.items():
            repre = repre_info["representation"]
            repre_name_low = repre["name"].lower()
            if repre_name_low in old_repres_by_name:
                old_repres_to_replace[repre_name_low] = (
                    old_repres_by_name.pop(repre_name_low)
                )
            else:
                old_repres_to_delete[repre_name_low] = (
                    old_repres_by_name.pop(repre_name_low)
                )

        archived_repres = list(io.find({
            # Check what is type of archived representation
            "type": "archived_repsentation",
            "parent": new_version_id
        }))
        archived_repres_by_name = {}
        for repre in archived_repres:
            repre_name_low = repre["name"].lower()
            archived_repres_by_name[repre_name_low] = repre

        self.delete_repre_files(old_repres)

        for repre_id, repre_info in published_repres.items():
            repre = copy.deepcopy(repre_info["representation"])
            repre_name_low = repre["name"].lower()

            repre["parent"] = new_master_version["_id"]
            # TODO change repre data and context (new anatomy)
            # TODO hardlink files

            # Replace current representation
            if repre_name_low in old_repres_to_replace:
                old_repre = old_repres_to_replace.pop(repre_name_low)
                repre["_id"] = old_repre["_id"]
                bulk_writes.append(
                    ReplaceOne(
                        {"_id": old_repre["_id"]},
                        repre
                    )
                )

            # Unarchive representation
            elif repre_name_low in archived_repres_by_name:
                archived_repre = archived_repres_by_name.pop(repre_name_low)
                old_id = archived_repre["old_id"]
                repre["_id"] = old_id
                bulk_writes.append(
                    ReplaceOne(
                        {"old_id": old_id},
                        repre
                    )
                )

            # Create representation
            else:
                repre["_id"] = io.ObjectId()
                bulk_writes.append(
                    InsertOne(repre)
                )

        # Archive not replaced old representations
        for repre_name_low, repre in old_repres_to_delete.items():
            # TODO delete their files

            # Replace archived representation (This is backup)
            # - should not happen to have both repre and archived repre
            if repre_name_low in archived_repres_by_name:
                archived_repre = archived_repres_by_name.pop(repre_name_low)
                repre["old_id"] = repre["_id"]
                repre["_id"] = archived_repre["_id"]
                repre["type"] = archived_repre["type"]
                bulk_writes.append(
                    ReplaceOne(
                        {"_id": archived_repre["_id"]},
                        repre
                    )
                )

            else:
                repre["old_id"] = repre["_id"]
                repre["_id"] = io.ObjectId()
                repre["type"] = "archived_representation"
                bulk_writes.append(
                    InsertOne(repre)
                )

        if bulk_writes:
            pass

    def delete_repre_files(self, repres):
        if not repres:
            return

        frame_splitter = "_-_FRAME_-_"
        files_to_delete = []
        for repre in repres:
            is_sequence = False
            if "frame" in repre["context"]:
                repre["context"]["frame"] = frame_splitter
                is_sequence = True

            template = repre["data"]["template"]
            context = repre["context"]
            context["root"] = api.registered_root()
            path = pipeline.format_template_with_optional_keys(
                context, template
            )
            path = os.path.normpath(path)
            if not is_sequence:
                if os.path.exists(path):
                    files_to_delete.append(path)
                continue

            dirpath = os.path.dirname(path)
            file_start = None
            file_end = None
            file_items = path.split(frame_splitter)
            if len(file_items) == 0:
                continue
            elif len(file_items) == 1:
                if path.startswith(frame_splitter):
                    file_end = file_items[0]
                else:
                    file_start = file_items[1]

            elif len(file_items) == 2:
                file_start, file_end = file_items

            else:
                raise ValueError((
                    "Representation template has `frame` key "
                    "more than once inside."
                ))

            for file_name in os.listdir(dirpath):
                check_name = str(file_name)
                if file_start and not check_name.startswith(file_start):
                    continue
                check_name.replace(file_start, "")

                if file_end and not check_name.endswith(file_end):
                    continue
                check_name.replace(file_end, "")

                # File does not have frame
                if not check_name:
                    continue

                files_to_delete.append(os.path.join(dirpath, file_name))

        renamed_files = []
        failed = False
        for file_path in files_to_delete:
            # TODO too robust for testing - should be easier in future
            _rename_path = file_path + ".BACKUP"
            rename_path = None
            max_index = 200
            cur_index = 1
            while True:
                if max_index >= cur_index:
                    raise Exception((
                        "Max while loop index reached! Can't make backup"
                        " for previous master version."
                    ))
                    break

                if not os.path.exists(_rename_path):
                    rename_path = _rename_path
                    break

                try:
                    os.remove(_rename_path)
                except Exception:
                    _rename_path = file_path + ".BACKUP{}".format(
                        str(cur_index)
                    )
                cur_index += 1

            try:
                args = (file_path, rename_path)
                os.rename(*args)
                renamed_files.append(args)
            except Exception:
                failed = True
                break

        if failed:
            for dst_name, src_name in renamed_files:
                os.rename(src_name, dst_name)

            raise AssertionError((
                "Could not create master version because it is not possible"
                " to replace current master files."
            ))

        for _, renamed_path in renamed_files:
            os.remove(renamed_path)

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
