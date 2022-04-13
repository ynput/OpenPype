import os
import copy
import clique
import errno
import shutil

from bson.objectid import ObjectId
from pymongo import InsertOne, ReplaceOne
import pyblish.api

from avalon import api, io
from openpype.lib import (
    create_hard_link,
    filter_profiles
)
from openpype.pipeline import schema


class IntegrateHeroVersion(pyblish.api.InstancePlugin):
    label = "Integrate Hero Version"
    # Must happen after IntegrateNew
    order = pyblish.api.IntegratorOrder + 0.1

    optional = True
    active = True

    # Families are modified using settings
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
    # QUESTION/TODO this process should happen on server if crashed due to
    # permissions error on files (files were used or user didn't have perms)
    # *but all other plugins must be sucessfully completed

    template_name_profiles = []
    _default_template_name = "hero"

    def process(self, instance):
        self.log.debug(
            "--- Integration of Hero version for subset `{}` begins.".format(
                instance.data.get("subset", str(instance))
            )
        )
        published_repres = instance.data.get("published_representations")
        if not published_repres:
            self.log.debug(
                "*** There are not published representations on the instance."
            )
            return

        template_key = self._get_template_key(instance)

        anatomy = instance.context.data["anatomy"]
        project_name = api.Session["AVALON_PROJECT"]
        if template_key not in anatomy.templates:
            self.log.warning((
                "!!! Anatomy of project \"{}\" does not have set"
                " \"{}\" template key!"
            ).format(project_name, template_key))
            return

        if "path" not in anatomy.templates[template_key]:
            self.log.warning((
                "!!! There is not set \"path\" template in \"{}\" anatomy"
                " for project \"{}\"."
            ).format(template_key, project_name))
            return

        hero_template = anatomy.templates[template_key]["path"]
        self.log.debug("`hero` template check was successful. `{}`".format(
            hero_template
        ))

        self.integrate_instance(instance, template_key, hero_template)

    def integrate_instance(self, instance, template_key, hero_template):
        anatomy = instance.context.data["anatomy"]
        published_repres = instance.data["published_representations"]
        hero_publish_dir = self.get_publish_dir(instance, template_key)

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
                " Skipping hero version publish."
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
        # WARNING due to this we must remove all files from hero publish dir
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
                instance_publish_dir, hero_publish_dir
            )
            other_file_paths_mapping.append((file_path, dst_filepath))

        # Current version
        old_version, old_repres = (
            self.current_hero_ents(src_version_entity)
        )

        old_repres_by_name = {
            repre["name"].lower(): repre for repre in old_repres
        }

        if old_version:
            new_version_id = old_version["_id"]
        else:
            new_version_id = ObjectId()

        new_hero_version = {
            "_id": new_version_id,
            "version_id": src_version_entity["_id"],
            "parent": src_version_entity["parent"],
            "type": "hero_version",
            "schema": "openpype:hero_version-1.0"
        }
        schema.validate(new_hero_version)

        # Don't make changes in database until everything is O.K.
        bulk_writes = []

        if old_version:
            self.log.debug("Replacing old hero version.")
            bulk_writes.append(
                ReplaceOne(
                    {"_id": new_hero_version["_id"]},
                    new_hero_version
                )
            )
        else:
            self.log.debug("Creating first hero version.")
            bulk_writes.append(
                InsertOne(new_hero_version)
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

        backup_hero_publish_dir = None
        if os.path.exists(hero_publish_dir):
            backup_hero_publish_dir = hero_publish_dir + ".BACKUP"
            max_idx = 10
            idx = 0
            _backup_hero_publish_dir = backup_hero_publish_dir
            while os.path.exists(_backup_hero_publish_dir):
                self.log.debug((
                    "Backup folder already exists."
                    " Trying to remove \"{}\""
                ).format(_backup_hero_publish_dir))

                try:
                    shutil.rmtree(_backup_hero_publish_dir)
                    backup_hero_publish_dir = _backup_hero_publish_dir
                    break
                except Exception:
                    self.log.info((
                        "Could not remove previous backup folder."
                        " Trying to add index to folder name"
                    ))

                _backup_hero_publish_dir = (
                    backup_hero_publish_dir + str(idx)
                )
                if not os.path.exists(_backup_hero_publish_dir):
                    backup_hero_publish_dir = _backup_hero_publish_dir
                    break

                if idx > max_idx:
                    raise AssertionError((
                        "Backup folders are fully occupied to max index \"{}\""
                    ).format(max_idx))
                    break

                idx += 1

            self.log.debug("Backup folder path is \"{}\"".format(
                backup_hero_publish_dir
            ))
            try:
                os.rename(hero_publish_dir, backup_hero_publish_dir)
            except PermissionError:
                raise AssertionError((
                    "Could not create hero version because it is not"
                    " possible to replace current hero files."
                ))
        try:
            src_to_dst_file_paths = []
            for repre_info in published_repres.values():

                # Skip if new repre does not have published repre files
                published_files = repre_info["published_files"]
                if len(published_files) == 0:
                    continue

                # Prepare anatomy data
                anatomy_data = copy.deepcopy(repre_info["anatomy_data"])
                anatomy_data.pop("version", None)

                # Get filled path to repre context
                anatomy_filled = anatomy.format(anatomy_data)
                template_filled = anatomy_filled[template_key]["path"]

                repre_data = {
                    "path": str(template_filled),
                    "template": hero_template
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
                repre["parent"] = new_hero_version["_id"]
                repre["context"] = repre_context
                repre["data"] = repre_data
                repre.pop("_id", None)

                # Prepare paths of source and destination files
                if len(published_files) == 1:
                    src_to_dst_file_paths.append(
                        (published_files[0], template_filled)
                    )
                else:
                    collections, remainders = clique.assemble(published_files)
                    if remainders or not collections or len(collections) > 1:
                        raise Exception((
                            "Integrity error. Files of published"
                            " representation is combination of frame"
                            " collections and single files. Collections:"
                            " `{}` Single files: `{}`"
                        ).format(str(collections), str(remainders)))

                    src_col = collections[0]

                    # Get head and tail for collection
                    frame_splitter = "_-_FRAME_SPLIT_-_"
                    anatomy_data["frame"] = frame_splitter
                    _anatomy_filled = anatomy.format(anatomy_data)
                    _template_filled = _anatomy_filled[template_key]["path"]
                    head, tail = _template_filled.split(frame_splitter)
                    padding = int(
                        anatomy.templates[template_key]["frame_padding"]
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

                # replace original file name with hero name in repre doc
                for index in range(len(repre.get("files"))):
                    file = repre.get("files")[index]
                    file_name = os.path.basename(file.get('path'))
                    for src_file, dst_file in src_to_dst_file_paths:
                        src_file_name = os.path.basename(src_file)
                        if src_file_name == file_name:
                            repre["files"][index]["path"] = self._update_path(
                                anatomy, repre["files"][index]["path"],
                                src_file, dst_file)

                            repre["files"][index]["hash"] = self._update_hash(
                                repre["files"][index]["hash"],
                                src_file_name, dst_file
                            )

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
                    repre["_id"] = ObjectId()
                    bulk_writes.append(
                        InsertOne(repre)
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
                    repre["_id"] = ObjectId()
                    repre["type"] = "archived_representation"
                    bulk_writes.append(
                        InsertOne(repre)
                    )

            if bulk_writes:
                io._database[io.Session["AVALON_PROJECT"]].bulk_write(
                    bulk_writes
                )

            # Remove backuped previous hero
            if (
                backup_hero_publish_dir is not None and
                os.path.exists(backup_hero_publish_dir)
            ):
                shutil.rmtree(backup_hero_publish_dir)

        except Exception:
            if (
                backup_hero_publish_dir is not None and
                os.path.exists(backup_hero_publish_dir)
            ):
                if os.path.exists(hero_publish_dir):
                    shutil.rmtree(hero_publish_dir)
                os.rename(backup_hero_publish_dir, hero_publish_dir)
            self.log.error((
                "!!! Creating of hero version failed."
                " Previous hero version maybe lost some data!"
            ))
            raise

        self.log.debug((
            "--- hero version integration for subset `{}`"
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

    def get_publish_dir(self, instance, template_key):
        anatomy = instance.context.data["anatomy"]
        template_data = copy.deepcopy(instance.data["anatomyData"])

        if "originalBasename" in instance.data:
            template_data.update({
                "originalBasename": instance.data.get("originalBasename")
            })

        if "folder" in anatomy.templates[template_key]:
            anatomy_filled = anatomy.format(template_data)
            publish_folder = anatomy_filled[template_key]["folder"]
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

            file_path = anatomy_filled[template_key]["path"]
            # Directory
            publish_folder = os.path.dirname(file_path)

        publish_folder = os.path.normpath(publish_folder)

        self.log.debug("hero publish dir: \"{}\"".format(publish_folder))

        return publish_folder

    def _get_template_key(self, instance):
        anatomy_data = instance.data["anatomyData"]
        task_data = anatomy_data.get("task") or {}
        task_name = task_data.get("name")
        task_type = task_data.get("type")
        host_name = instance.context.data["hostName"]
        # TODO raise error if Hero not set?
        family = self.main_family_from_instance(instance)
        key_values = {
            "families": family,
            "task_names": task_name,
            "task_types": task_type,
            "hosts": host_name
        }
        profile = filter_profiles(
            self.template_name_profiles,
            key_values,
            logger=self.log
        )
        if profile:
            template_name = profile["template_name"]
        else:
            template_name = self._default_template_name
        return template_name

    def main_family_from_instance(self, instance):
        """Returns main family of entered instance."""
        family = instance.data.get("family")
        if not family:
            family = instance.data["families"][0]
        return family

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
            create_hard_link(src_path, dst_path)
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

    def current_hero_ents(self, version):
        hero_version = io.find_one({
            "parent": version["parent"],
            "type": "hero_version"
        })

        if not hero_version:
            return (None, [])

        hero_repres = list(io.find({
            "parent": hero_version["_id"],
            "type": "representation"
        }))
        return (hero_version, hero_repres)

    def _update_path(self, anatomy, path, src_file, dst_file):
        """
            Replaces source path with new hero path

            'path' contains original path with version, must be replaced with
            'hero' path (with 'hero' label and without version)

            Args:
                anatomy (Anatomy) - to get rootless style of path
                path (string) - path from DB
                src_file (string) - original file path
                dst_file (string) - hero file path
        """
        _, rootless = anatomy.find_root_template_from_path(dst_file)
        _, rtls_src = anatomy.find_root_template_from_path(src_file)
        return path.replace(rtls_src, rootless)

    def _update_hash(self, hash, src_file_name, dst_file):
        """
            Updates hash value with proper hero name
        """
        src_file_name = self._get_name_without_ext(src_file_name)
        hero_file_name = self._get_name_without_ext(dst_file)
        return hash.replace(src_file_name, hero_file_name)

    def _get_name_without_ext(self, value):
        file_name = os.path.basename(value)
        file_name, _ = os.path.splitext(file_name)
        return file_name
