import os
import copy
import clique
import errno
import shutil

from pymongo import InsertOne, ReplaceOne
import pyblish.api
from avalon import api, io, schema
from avalon.vendor import filelink


class IntegrateMasterVersion(pyblish.api.InstancePlugin):
    label = "Integrate Master Version"
    # Must happen after IntegrateNew
    order = pyblish.api.IntegratorOrder + 0.1

    optional = True

    families = [
        "model",
        "rig",
        "setdress",
        "look",
        "pointcache",
        "animation"
    ]

    # Can specify representation names that will be ignored (lower case)
    ignored_representation_names = []
    db_representation_context_keys = [
        "project", "asset", "task", "subset", "representation",
        "family", "hierarchy", "task", "username"
    ]
    # TODO add family filtering
    # QUESTION/TODO this process should happen on server if crashed due to
    # permissions error on files (files were used or user didn't have perms)
    # *but all other plugins must be sucessfully completed

    def process(self, instance):
        self.log.debug(
            "--- Integration of Master version for subset `{}` begins.".format(
                instance.data.get("subset", str(instance))
            )
        )
        published_repres = instance.data.get("published_representations")
        if not published_repres:
            self.log.debug(
                "*** There are not published representations on the instance."
            )
            return

        project_name = api.Session["AVALON_PROJECT"]

        # TODO raise error if master not set?
        anatomy = instance.context.data["anatomy"]
        if "master" not in anatomy.templates:
            self.log.warning("!!! Anatomy does not have set `master` key!")
            return

        if "path" not in anatomy.templates["master"]:
            self.log.warning((
                "!!! There is not set `path` template in `master` anatomy"
                " for project \"{}\"."
            ).format(project_name))
            return

        master_template = anatomy.templates["master"]["path"]
        self.log.debug("`Master` template check was successful. `{}`".format(
            master_template
        ))

        master_publish_dir = self.get_publish_dir(instance)

        src_version_entity = instance.data.get("versionEntity")
        filtered_repre_ids = []
        for repre_id, repre_info in published_repres.items():
            repre = repre_info["representation"]
            if repre["name"].lower() in self.ignored_representation_names:
                self.log.debug(
                    "Filtering representation with name: `{}`".format(
                        repre["name"].lower()
                    )
                )
                filtered_repre_ids.append(repre_id)

        for repre_id in filtered_repre_ids:
            published_repres.pop(repre_id, None)

        if not published_repres:
            self.log.debug(
                "*** All published representations were filtered by name."
            )
            return

        if src_version_entity is None:
            self.log.debug((
                "Published version entity was not sent in representation data."
                " Querying entity from database."
            ))
            src_version_entity = (
                self.version_from_representations(published_repres)
            )

        if not src_version_entity:
            self.log.warning((
                "!!! Can't find origin version in database."
                " Skipping Master version publish."
            ))
            return

        all_copied_files = []
        transfers = instance.data.get("transfers", list())
        for _src, dst in transfers:
            dst = os.path.normpath(dst)
            if dst not in all_copied_files:
                all_copied_files.append(dst)

        hardlinks = instance.data.get("hardlinks", list())
        for _src, dst in hardlinks:
            dst = os.path.normpath(dst)
            if dst not in all_copied_files:
                all_copied_files.append(dst)

        all_repre_file_paths = []
        for repre_info in published_repres.values():
            published_files = repre_info.get("published_files") or []
            for file_path in published_files:
                file_path = os.path.normpath(file_path)
                if file_path not in all_repre_file_paths:
                    all_repre_file_paths.append(file_path)

        # TODO this is not best practice of getting resources for publish
        # WARNING due to this we must remove all files from master publish dir
        instance_publish_dir = os.path.normpath(
            instance.data["publishDir"]
        )
        other_file_paths_mapping = []
        for file_path in all_copied_files:
            # Check if it is from publishDir
            if not file_path.startswith(instance_publish_dir):
                continue

            if file_path in all_repre_file_paths:
                continue

            dst_filepath = file_path.replace(
                instance_publish_dir, master_publish_dir
            )
            other_file_paths_mapping.append((file_path, dst_filepath))

        # Current version
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
        schema.validate(new_master_version)

        # Don't make changes in database until everything is O.K.
        bulk_writes = []

        if old_version:
            self.log.debug("Replacing old master version.")
            bulk_writes.append(
                ReplaceOne(
                    {"_id": new_master_version["_id"]},
                    new_master_version
                )
            )
        else:
            self.log.debug("Creating first master version.")
            bulk_writes.append(
                InsertOne(new_master_version)
            )

        # Separate old representations into `to replace` and `to delete`
        old_repres_to_replace = {}
        old_repres_to_delete = {}
        for repre_info in published_repres.values():
            repre = repre_info["representation"]
            repre_name_low = repre["name"].lower()
            if repre_name_low in old_repres_by_name:
                old_repres_to_replace[repre_name_low] = (
                    old_repres_by_name.pop(repre_name_low)
                )

        if old_repres_by_name:
            old_repres_to_delete = old_repres_by_name

        archived_repres = list(io.find({
            # Check what is type of archived representation
            "type": "archived_repsentation",
            "parent": new_version_id
        }))
        archived_repres_by_name = {}
        for repre in archived_repres:
            repre_name_low = repre["name"].lower()
            archived_repres_by_name[repre_name_low] = repre

        backup_master_publish_dir = None
        if os.path.exists(master_publish_dir):
            backup_master_publish_dir = master_publish_dir + ".BACKUP"
            max_idx = 10
            idx = 0
            _backup_master_publish_dir = backup_master_publish_dir
            while os.path.exists(_backup_master_publish_dir):
                self.log.debug((
                    "Backup folder already exists."
                    " Trying to remove \"{}\""
                ).format(_backup_master_publish_dir))

                try:
                    shutil.rmtree(_backup_master_publish_dir)
                    backup_master_publish_dir = _backup_master_publish_dir
                    break
                except Exception:
                    self.log.info((
                        "Could not remove previous backup folder."
                        " Trying to add index to folder name"
                    ))

                _backup_master_publish_dir = (
                    backup_master_publish_dir + str(idx)
                )
                if not os.path.exists(_backup_master_publish_dir):
                    backup_master_publish_dir = _backup_master_publish_dir
                    break

                if idx > max_idx:
                    raise AssertionError((
                        "Backup folders are fully occupied to max index \"{}\""
                    ).format(max_idx))
                    break

                idx += 1

            self.log.debug("Backup folder path is \"{}\"".format(
                backup_master_publish_dir
            ))
            try:
                os.rename(master_publish_dir, backup_master_publish_dir)
            except PermissionError:
                raise AssertionError((
                    "Could not create master version because it is not"
                    " possible to replace current master files."
                ))
        try:
            src_to_dst_file_paths = []
            for repre_info in published_repres.values():

                # Skip if new repre does not have published repre files
                published_files = repre_info["published_files"]
                if len(published_files) == 0:
                    continue

                # Prepare anatomy data
                anatomy_data = repre_info["anatomy_data"]
                anatomy_data.pop("version", None)

                # Get filled path to repre context
                anatomy_filled = anatomy.format(anatomy_data)
                template_filled = anatomy_filled["master"]["path"]

                repre_data = {
                    "path": str(template_filled),
                    "template": master_template
                }
                repre_context = template_filled.used_values
                for key in self.db_representation_context_keys:
                    if (
                        key in repre_context or
                        key not in anatomy_data
                    ):
                        continue

                    repre_context[key] = anatomy_data[key]

                # Prepare new repre
                repre = copy.deepcopy(repre_info["representation"])
                repre["parent"] = new_master_version["_id"]
                repre["context"] = repre_context
                repre["data"] = repre_data
                repre.pop("_id", None)

                schema.validate(repre)

                repre_name_low = repre["name"].lower()
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
                    archived_repre = archived_repres_by_name.pop(
                        repre_name_low
                    )
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

                # Prepare paths of source and destination files
                if len(published_files) == 1:
                    src_to_dst_file_paths.append(
                        (published_files[0], template_filled)
                    )
                    continue

                collections, remainders = clique.assemble(published_files)
                if remainders or not collections or len(collections) > 1:
                    raise Exception((
                        "Integrity error. Files of published representation "
                        "is combination of frame collections and single files."
                        "Collections: `{}` Single files: `{}`"
                    ).format(str(collections), str(remainders)))

                src_col = collections[0]

                # Get head and tail for collection
                frame_splitter = "_-_FRAME_SPLIT_-_"
                anatomy_data["frame"] = frame_splitter
                _anatomy_filled = anatomy.format(anatomy_data)
                _template_filled = _anatomy_filled["master"]["path"]
                head, tail = _template_filled.split(frame_splitter)
                padding = int(
                    anatomy.templates["render"].get(
                        "frame_padding",
                        anatomy.templates["render"].get("padding")
                    )
                )

                dst_col = clique.Collection(
                    head=head, padding=padding, tail=tail
                )
                dst_col.indexes.clear()
                dst_col.indexes.update(src_col.indexes)
                for src_file, dst_file in zip(src_col, dst_col):
                    src_to_dst_file_paths.append(
                        (src_file, dst_file)
                    )

            self.path_checks = []

            # Copy(hardlink) paths of source and destination files
            # TODO should we *only* create hardlinks?
            # TODO should we keep files for deletion until this is successful?
            for src_path, dst_path in src_to_dst_file_paths:
                self.copy_file(src_path, dst_path)

            for src_path, dst_path in other_file_paths_mapping:
                self.copy_file(src_path, dst_path)

            # Archive not replaced old representations
            for repre_name_low, repre in old_repres_to_delete.items():
                # Replace archived representation (This is backup)
                # - should not happen to have both repre and archived repre
                if repre_name_low in archived_repres_by_name:
                    archived_repre = archived_repres_by_name.pop(
                        repre_name_low
                    )
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
                io._database[io.Session["AVALON_PROJECT"]].bulk_write(
                    bulk_writes
                )

            # Remove backuped previous master
            if (
                backup_master_publish_dir is not None and
                os.path.exists(backup_master_publish_dir)
            ):
                shutil.rmtree(backup_master_publish_dir)

        except Exception:
            if (
                backup_master_publish_dir is not None and
                os.path.exists(backup_master_publish_dir)
            ):
                os.rename(backup_master_publish_dir, master_publish_dir)
            self.log.error((
                "!!! Creating of Master version failed."
                " Previous master version maybe lost some data!"
            ))
            raise

        self.log.debug((
            "--- Master version integration for subset `{}`"
            " seems to be successful."
        ).format(
            instance.data.get("subset", str(instance))
        ))

    def get_all_files_from_path(self, path):
        files = []
        for (dir_path, dir_names, file_names) in os.walk(path):
            for file_name in file_names:
                _path = os.path.join(dir_path, file_name)
                files.append(_path)
        return files

    def get_publish_dir(self, instance):
        anatomy = instance.context.data["anatomy"]
        template_data = copy.deepcopy(instance.data["anatomyData"])

        if "folder" in anatomy.templates["master"]:
            anatomy_filled = anatomy.format(template_data)
            publish_folder = anatomy_filled["master"]["folder"]
        else:
            # This is for cases of Deprecated anatomy without `folder`
            # TODO remove when all clients have solved this issue
            template_data.update({
                "frame": "FRAME_TEMP",
                "representation": "TEMP"
            })
            anatomy_filled = anatomy.format(template_data)
            # solve deprecated situation when `folder` key is not underneath
            # `publish` anatomy
            project_name = api.Session["AVALON_PROJECT"]
            self.log.warning((
                "Deprecation warning: Anatomy does not have set `folder`"
                " key underneath `publish` (in global of for project `{}`)."
            ).format(project_name))

            file_path = anatomy_filled["master"]["path"]
            # Directory
            publish_folder = os.path.dirname(file_path)

        publish_folder = os.path.normpath(publish_folder)

        self.log.debug("Master publish dir: \"{}\"".format(publish_folder))

        return publish_folder

    def copy_file(self, src_path, dst_path):
        # TODO check drives if are the same to check if cas hardlink
        dirname = os.path.dirname(dst_path)

        try:
            os.makedirs(dirname)
            self.log.debug("Folder(s) created: \"{}\"".format(dirname))
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                self.log.error("An unexpected error occurred.", exc_info=True)
                raise

            self.log.debug("Folder already exists: \"{}\"".format(dirname))

        self.log.debug("Copying file \"{}\" to \"{}\"".format(
            src_path, dst_path
        ))

        # First try hardlink and copy if paths are cross drive
        try:
            filelink.create(src_path, dst_path, filelink.HARDLINK)
            # Return when successful
            return

        except OSError as exc:
            # re-raise exception if different than cross drive path
            if exc.errno != errno.EXDEV:
                raise

        shutil.copy(src_path, dst_path)

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
