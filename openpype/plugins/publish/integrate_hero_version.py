import os
import copy
import clique
import errno
import shutil

import pyblish.api

from openpype import AYON_SERVER_ENABLED
from openpype.client import (
    get_version_by_id,
    get_hero_version_by_subset_id,
    get_archived_representations,
    get_representations,
)
from openpype.client.operations import (
    OperationsSession,
    new_hero_version_doc,
    prepare_hero_version_update_data,
    prepare_representation_update_data,
)
from openpype.lib import create_hard_link
from openpype.pipeline import (
    schema
)
from openpype.pipeline.publish import get_publish_template_name


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
        "family", "hierarchy", "task", "username", "user"
    ]
    # QUESTION/TODO this process should happen on server if crashed due to
    # permissions error on files (files were used or user didn't have perms)
    # *but all other plugins must be sucessfully completed

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
                "*** There are no published representations on the instance."
            )
            return

        anatomy = instance.context.data["anatomy"]
        project_name = anatomy.project_name

        template_key = self._get_template_key(project_name, instance)

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

        self.integrate_instance(
            instance, project_name, template_key, hero_template
        )

    def integrate_instance(
        self, instance, project_name, template_key, hero_template
    ):
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
            src_version_entity = self.version_from_representations(
                project_name, published_repres
            )

        if not src_version_entity:
            self.log.warning((
                "!!! Can't find origin version in database."
                " Skipping hero version publish."
            ))
            return

        if AYON_SERVER_ENABLED and src_version_entity["name"] == 0:
            self.log.debug(
                "Version 0 cannot have hero version. Skipping."
            )
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
        old_version, old_repres = self.current_hero_ents(
            project_name, src_version_entity
        )

        old_repres_by_name = {
            repre["name"].lower(): repre for repre in old_repres
        }

        op_session = OperationsSession()

        entity_id = None
        if old_version:
            entity_id = old_version["_id"]

        if AYON_SERVER_ENABLED:
            new_hero_version = new_hero_version_doc(
                src_version_entity["parent"],
                copy.deepcopy(src_version_entity["data"]),
                src_version_entity["name"],
                entity_id=entity_id
            )
        else:
            new_hero_version = new_hero_version_doc(
                src_version_entity["_id"],
                src_version_entity["parent"],
                entity_id=entity_id
            )

        if old_version:
            self.log.debug("Replacing old hero version.")
            update_data = prepare_hero_version_update_data(
                old_version, new_hero_version
            )
            op_session.update_entity(
                project_name,
                new_hero_version["type"],
                old_version["_id"],
                update_data
            )
        else:
            self.log.debug("Creating first hero version.")
            op_session.create_entity(
                project_name, new_hero_version["type"], new_hero_version
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

        archived_repres = list(get_archived_representations(
            project_name,
            # Check what is type of archived representation
            version_ids=[new_hero_version["_id"]]
        ))
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
                    self.log.info(
                        "Could not remove previous backup folder."
                        " Trying to add index to folder name."
                    )

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
            path_template_obj = anatomy.templates_obj[template_key]["path"]
            for repre_info in published_repres.values():

                # Skip if new repre does not have published repre files
                published_files = repre_info["published_files"]
                if len(published_files) == 0:
                    continue

                # Prepare anatomy data
                anatomy_data = copy.deepcopy(repre_info["anatomy_data"])
                anatomy_data.pop("version", None)

                # Get filled path to repre context
                template_filled = path_template_obj.format_strict(anatomy_data)
                repre_data = {
                    "path": str(template_filled),
                    "template": hero_template
                }
                repre_context = template_filled.used_values
                for key in self.db_representation_context_keys:
                    value = anatomy_data.get(key)
                    if value is not None:
                        repre_context[key] = value

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
                    _template_filled = path_template_obj.format_strict(
                        anatomy_data
                    )
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
                    update_data = prepare_representation_update_data(
                        old_repre, repre)

                    # Keep previously synchronized sites up-to-date
                    #   by comparing old and new sites and adding old sites
                    #   if missing in new ones
                    # Prepare all sites from all files in old representation
                    old_site_names = set()
                    for file_info in old_repre.get("files", []):
                        old_site_names |= {
                            site["name"]
                            for site in file_info["sites"]
                        }

                    for file_info in update_data.get("files", []):
                        file_info.setdefault("sites", [])
                        file_info_site_names = {
                            site["name"]
                            for site in file_info["sites"]
                        }
                        for site_name in old_site_names:
                            if site_name not in file_info_site_names:
                                file_info["sites"].append({
                                    "name": site_name
                                })

                    op_session.update_entity(
                        project_name,
                        old_repre["type"],
                        old_repre["_id"],
                        update_data
                    )

                # Unarchive representation
                elif repre_name_low in archived_repres_by_name:
                    archived_repre = archived_repres_by_name.pop(
                        repre_name_low
                    )
                    repre["_id"] = archived_repre["old_id"]
                    update_data = prepare_representation_update_data(
                        archived_repre, repre)
                    op_session.update_entity(
                        project_name,
                        old_repre["type"],
                        archived_repre["_id"],
                        update_data
                    )

                # Create representation
                else:
                    repre.pop("_id", None)
                    op_session.create_entity(project_name, "representation",
                                             repre)

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

                    changes = {"old_id": repre["_id"],
                               "_id": archived_repre["_id"],
                               "type": archived_repre["type"]}
                    op_session.update_entity(project_name,
                                             archived_repre["type"],
                                             archived_repre["_id"],
                                             changes)
                else:
                    repre["old_id"] = repre.pop("_id")
                    repre["type"] = "archived_representation"
                    op_session.create_entity(project_name,
                                             "archived_representation",
                                             repre)

            op_session.commit()

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
            template_obj = anatomy.templates_obj[template_key]["folder"]
            publish_folder = template_obj.format_strict(template_data)
        else:
            # This is for cases of Deprecated anatomy without `folder`
            # TODO remove when all clients have solved this issue
            self.log.warning((
                "Deprecation warning: Anatomy does not have set `folder`"
                " key underneath `publish` (in global of for project `{}`)."
            ).format(anatomy.project_name))
            # solve deprecated situation when `folder` key is not underneath
            # `publish` anatomy
            template_data.update({
                "frame": "FRAME_TEMP",
                "representation": "TEMP"
            })
            template_obj = anatomy.templates_obj[template_key]["path"]
            file_path = template_obj.format_strict(template_data)

            # Directory
            publish_folder = os.path.dirname(file_path)

        publish_folder = os.path.normpath(publish_folder)

        self.log.debug("hero publish dir: \"{}\"".format(publish_folder))

        return publish_folder

    def _get_template_key(self, project_name, instance):
        anatomy_data = instance.data["anatomyData"]
        task_info = anatomy_data.get("task") or {}
        host_name = instance.context.data["hostName"]

        # TODO raise error if Hero not set?
        family = self.main_family_from_instance(instance)

        return get_publish_template_name(
            project_name,
            host_name,
            family,
            task_info.get("name"),
            task_info.get("type"),
            project_settings=instance.context.data["project_settings"],
            hero=True,
            logger=self.log
        )

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
            # re-raise exception if different than
            # EXDEV - cross drive path
            # EINVAL - wrong format, must be NTFS
            self.log.debug("Hardlink failed with errno:'{}'".format(exc.errno))
            if exc.errno not in [errno.EXDEV, errno.EINVAL]:
                raise

        shutil.copy(src_path, dst_path)

    def version_from_representations(self, project_name, repres):
        for repre in repres:
            version = get_version_by_id(project_name, repre["parent"])
            if version:
                return version

    def current_hero_ents(self, project_name, version):
        hero_version = get_hero_version_by_subset_id(
            project_name, version["parent"]
        )

        if not hero_version:
            return (None, [])

        hero_repres = list(get_representations(
            project_name, version_ids=[hero_version["_id"]]
        ))
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
