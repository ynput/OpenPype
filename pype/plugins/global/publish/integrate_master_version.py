import os
import copy
import logging
import clique
import errno

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
    db_representation_context_keys = [
        "project", "asset", "task", "subset", "representation",
        "family", "hierarchy", "task", "username"
    ]

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
        if "publish" not in anatomy.templates:
            self.log.warning("!!! Anatomy does not have set publish key!")
            return

        if "master" not in anatomy.templates["publish"]:
            self.log.warning((
                "!!! There is not set \"master\" template for project \"{}\""
            ).format(project_name))
            return

        master_template = anatomy.templates["publish"]["master"]

        self.log.debug("`Master` template check was successful. `{}`".format(
            master_template
        ))

        src_version_entity = None

        filtered_repre_ids = []
        for repre_id, repre_info in published_repres.items():
            repre = repre_info["representation"]
            if src_version_entity is None:
                src_version_entity = repre_info.get("version_entity")

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
        for repre_id, repre_info in published_repres.items():
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

        self.delete_repre_files(old_repres)

        src_to_dst_file_paths = []
        for repre_id, repre_info in published_repres.items():

            # Skip if new repre does not have published repre files
            published_files = repre_info["published_files"]
            if len(published_files) == 0:
                continue

            # Prepare anatomy data
            anatomy_data = repre_info["anatomy_data"]
            anatomy_data.pop("version", None)

            # Get filled path to repre context
            anatomy_filled = anatomy.format(anatomy_data)
            template_filled = anatomy_filled["publish"]["master"]

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

            # Prepare paths of source and destination files
            if len(published_files) == 1:
                src_to_dst_file_paths.append(
                    (published_files[0], template_filled)
                )
                continue

            collections, remainders = clique.assemble(published_files)
            if remainders or not collections or len(collections) > 1:
                raise Exception((
                    "Integrity error. Files of published representation"
                    " is combination of frame collections and single files."
                    "Collections: `{}` Single files: `{}`"
                ).format(str(collections), str(remainders)))

            src_col = collections[0]

            # Get head and tail for collection
            frame_splitter = "_-_FRAME_SPLIT_-_"
            anatomy_data["frame"] = frame_splitter
            _anatomy_filled = anatomy.format(anatomy_data)
            _template_filled = _anatomy_filled["publish"]["master"]
            head, tail = _template_filled.split(frame_splitter)
            padding = (
                anatomy.templates["render"]["padding"]
            )

            dst_col = clique.Collection(head=head, padding=padding, tail=tail)
            dst_col.indexes.clear()
            dst_col.indexes.update(src_col.indexes)
            for src_file, dst_file in zip(src_col, dst_col):
                src_to_dst_file_paths.append(
                    (src_file, dst_file)
                )

        # Copy(hardlink) paths of source and destination files
        # TODO should we *only* create hardlinks?
        # TODO less logs about drives
        # TODO should we keep files for deletion until this is successful?
        for src_path, dst_path in src_to_dst_file_paths:
            self.create_hardlink(src_path, dst_path)

        # Archive not replaced old representations
        for repre_name_low, repre in old_repres_to_delete.items():
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
            io._database[io.Session["AVALON_PROJECT"]].bulk_write(bulk_writes)

        self.log.debug((
            "--- End of Master version integration for subset `{}`."
        ).format(
            instance.data.get("subset", str(instance))
        ))

    def create_hardlink(self, src_path, dst_path):
        dst_path = self.path_root_check(dst_path)
        src_path = self.path_root_check(src_path)

        dirname = os.path.dirname(dst_path)

        try:
            os.makedirs(dirname)
            self.log.debug("Folder created: \"{}\"".format(dirname))
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                self.log.error("An unexpected error occurred.", exc_info=True)
                raise

            self.log.debug("Folder already exists: \"{}\"".format(dirname))

        self.log.debug("Copying file \"{}\" to \"{}\"".format(
            src_path, dst_path
        ))
        # TODO check if file exists!!!
        # - uncomplete publish may cause that file already exists
        filelink.create(src_path, dst_path, filelink.HARDLINK)

    def path_root_check(self, path):
        normalized_path = os.path.normpath(path)
        forward_slash_path = normalized_path.replace("\\", "/")

        drive, _path = os.path.splitdrive(normalized_path)
        if os.path.exists(drive + "/"):
            self.log.debug(
                "Drive \"{}\" exist. Nothing to change.".format(drive)
            )
            return normalized_path

        path_env_key = "PYPE_STUDIO_PROJECTS_PATH"
        mount_env_key = "PYPE_STUDIO_PROJECTS_MOUNT"
        missing_envs = []
        if path_env_key not in os.environ:
            missing_envs.append(path_env_key)

        if mount_env_key not in os.environ:
            missing_envs.append(mount_env_key)

        if missing_envs:
            _add_s = ""
            if len(missing_envs) > 1:
                _add_s = "s"

            self.log.warning((
                "Can't replace MOUNT drive path to UNC path due to missing"
                " environment variable{}: `{}`. This may cause issues during"
                " publishing process."
            ).format(_add_s, ", ".join(missing_envs)))

            return normalized_path

        unc_root = os.environ[path_env_key].replace("\\", "/")
        mount_root = os.environ[mount_env_key].replace("\\", "/")

        # --- Remove slashes at the end of mount and unc roots ---
        while unc_root.endswith("/"):
            unc_root = unc_root[:-1]

        while mount_root.endswith("/"):
            mount_root = mount_root[:-1]
        # ---

        if forward_slash_path.startswith(unc_root):
            self.log.debug((
                "Path already starts with UNC root: \"{}\""
            ).format(unc_root))
            return normalized_path

        if not forward_slash_path.startswith(mount_root):
            self.log.warning((
                "Path do not start with MOUNT root \"{}\" "
                "set in environment variable \"{}\""
            ).format(unc_root, mount_env_key))
            return normalized_path

        # Replace Mount root with Unc root
        path = unc_root + forward_slash_path[len(mount_root):]

        return os.path.normpath(path)

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
            self.log.debug(
                "Preparing file for deletion: `{}`".format(file_path)
            )
            rename_path = file_path + ".BACKUP"

            max_index = 10
            cur_index = 0
            _rename_path = None
            while os.path.exists(rename_path):
                if _rename_path is None:
                    _rename_path = rename_path

                if cur_index >= max_index:
                    self.log.warning((
                        "Max while loop index reached! Can't make backup"
                        " for previous master version."
                    ))
                    failed = True
                    break

                if not os.path.exists(_rename_path):
                    rename_path = _rename_path
                    break

                try:
                    os.remove(_rename_path)
                    self.log.debug(
                        "Deleted old backup file: \"{}\"".format(_rename_path)
                    )
                except Exception:
                    self.log.warning(
                        "Could not delete old backup file \"{}\".".format(
                            _rename_path
                        ),
                        exc_info=True
                    )
                    _rename_path = file_path + ".BACKUP{}".format(
                        str(cur_index)
                    )
                cur_index += 1

            # Skip if any already failed
            if failed:
                break

            try:
                args = (file_path, rename_path)
                os.rename(*args)
                renamed_files.append(args)
            except Exception:
                self.log.warning(
                    "Could not rename file `{}` to `{}`".format(
                        file_path, rename_path
                    ),
                    exc_info=True
                )
                failed = True
                break

        if failed:
            # Rename back old renamed files
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
