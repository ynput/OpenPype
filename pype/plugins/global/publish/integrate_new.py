import os
from os.path import getsize
import logging
import sys
import copy
import clique
import errno
import six
import re
import shutil

from pymongo import DeleteOne, InsertOne
import pyblish.api
from avalon import io
from avalon.vendor import filelink
import pype.api
from datetime import datetime

# this is needed until speedcopy for linux is fixed
if sys.platform == "win32":
    from speedcopy import copyfile
else:
    from shutil import copyfile

log = logging.getLogger(__name__)


class IntegrateAssetNew(pyblish.api.InstancePlugin):
    """Resolve any dependency issues

    This plug-in resolves any paths which, if not updated might break
    the published file.

    The order of families is important, when working with lookdev you want to
    first publish the texture, update the texture paths in the nodes and then
    publish the shading network. Same goes for file dependent assets.

    Requirements for instance to be correctly integrated

    instance.data['representations'] - must be a list and each member
    must be a dictionary with following data:
        'files': list of filenames for sequence, string for single file.
                 Only the filename is allowed, without the folder path.
        'stagingDir': "path/to/folder/with/files"
        'name': representation name (usually the same as extension)
        'ext': file extension
    optional data
        "frameStart"
        "frameEnd"
        'fps'
        "data": additional metadata for each representation.
    """

    label = "Integrate Asset New"
    order = pyblish.api.IntegratorOrder
    families = ["workfile",
                "pointcache",
                "camera",
                "animation",
                "model",
                "mayaAscii",
                "setdress",
                "layout",
                "ass",
                "vdbcache",
                "scene",
                "vrayproxy",
                "render",
                "prerender",
                "imagesequence",
                "review",
                "rendersetup",
                "rig",
                "plate",
                "look",
                "lut",
                "audio",
                "yetiRig",
                "yeticache",
                "nukenodes",
                "gizmo",
                "source",
                "matchmove",
                "image",
                "source",
                "assembly",
                "fbx",
                "textures",
                "action",
                "harmony.template",
                "harmony.palette",
                "editorial",
                "background"
                ]
    exclude_families = ["clip"]
    db_representation_context_keys = [
        "project", "asset", "task", "subset", "version", "representation",
        "family", "hierarchy", "task", "username"
    ]
    default_template_name = "publish"
    template_name_profiles = None

    # file_url : file_size of all published and uploaded files
    integrated_file_sizes = {}

    TMP_FILE_EXT = 'tmp'  # suffix to denote temporary files, use without '.'

    def process(self, instance):
        self.integrated_file_sizes = {}
        if [ef for ef in self.exclude_families
                if instance.data["family"] in ef]:
            return

        try:
            self.register(instance)
            self.log.info("Integrated Asset in to the database ...")
            self.log.info("instance.data: {}".format(instance.data))
            self.handle_destination_files(self.integrated_file_sizes,
                                          'finalize')
        except Exception:
            # clean destination
            self.log.critical("Error when registering", exc_info=True)
            self.handle_destination_files(self.integrated_file_sizes, 'remove')
            six.reraise(*sys.exc_info())

    def register(self, instance):
        # Required environment variables
        anatomy_data = instance.data["anatomyData"]

        io.install()

        context = instance.context

        project_entity = instance.data["projectEntity"]

        context_asset_name = context.data["assetEntity"]["name"]

        asset_name = instance.data["asset"]
        asset_entity = instance.data.get("assetEntity")
        if not asset_entity or asset_entity["name"] != context_asset_name:
            asset_entity = io.find_one({
                "type": "asset",
                "name": asset_name,
                "parent": project_entity["_id"]
            })
            assert asset_entity, (
                "No asset found by the name \"{0}\" in project \"{1}\""
            ).format(asset_name, project_entity["name"])

            instance.data["assetEntity"] = asset_entity

            # update anatomy data with asset specific keys
            # - name should already been set
            hierarchy = ""
            parents = asset_entity["data"]["parents"]
            if parents:
                hierarchy = "/".join(parents)
            anatomy_data["hierarchy"] = hierarchy

        task_name = instance.data.get("task")
        if task_name:
            anatomy_data["task"] = task_name

        anatomy_data["family"] = instance.data.get("family")

        stagingdir = instance.data.get("stagingDir")
        if not stagingdir:
            self.log.info((
                "{0} is missing reference to staging directory."
                " Will try to get it from representation."
            ).format(instance))

        else:
            self.log.debug(
                "Establishing staging directory @ {0}".format(stagingdir)
            )

        # Ensure at least one file is set up for transfer in staging dir.
        repres = instance.data.get("representations")
        assert repres, "Instance has no files to transfer"
        assert isinstance(repres, (list, tuple)), (
            "Instance 'files' must be a list, got: {0} {1}".format(
                str(type(repres)), str(repres)
            )
        )

        subset = self.get_subset(asset_entity, instance)
        instance.data["subsetEntity"] = subset

        version_number = instance.data["version"]
        self.log.debug("Next version: v{}".format(version_number))

        version_data = self.create_version_data(context, instance)

        version_data_instance = instance.data.get('versionData')
        if version_data_instance:
            version_data.update(version_data_instance)

        # TODO rename method from `create_version` to
        # `prepare_version` or similar...
        version = self.create_version(
            subset=subset,
            version_number=version_number,
            data=version_data
        )

        self.log.debug("Creating version ...")

        new_repre_names_low = [_repre["name"].lower() for _repre in repres]

        existing_version = io.find_one({
            'type': 'version',
            'parent': subset["_id"],
            'name': version_number
        })

        if existing_version is None:
            version_id = io.insert_one(version).inserted_id
        else:
            # Check if instance have set `append` mode which cause that
            # only replicated representations are set to archive
            append_repres = instance.data.get("append", False)

            # Update version data
            # TODO query by _id and
            io.update_many({
                'type': 'version',
                'parent': subset["_id"],
                'name': version_number
            }, {
                '$set': version
            })
            version_id = existing_version['_id']

            # Find representations of existing version and archive them
            current_repres = list(io.find({
                "type": "representation",
                "parent": version_id
            }))
            bulk_writes = []
            for repre in current_repres:
                if append_repres:
                    # archive only duplicated representations
                    if repre["name"].lower() not in new_repre_names_low:
                        continue
                # Representation must change type,
                # `_id` must be stored to other key and replaced with new
                # - that is because new representations should have same ID
                repre_id = repre["_id"]
                bulk_writes.append(DeleteOne({"_id": repre_id}))

                repre["orig_id"] = repre_id
                repre["_id"] = io.ObjectId()
                repre["type"] = "archived_representation"
                bulk_writes.append(InsertOne(repre))

            # bulk updates
            if bulk_writes:
                io._database[io.Session["AVALON_PROJECT"]].bulk_write(
                    bulk_writes
                )

        version = io.find_one({"_id": version_id})
        instance.data["versionEntity"] = version

        existing_repres = list(io.find({
            "parent": version_id,
            "type": "archived_representation"
        }))

        instance.data['version'] = version['name']

        intent_value = instance.context.data.get("intent")
        if intent_value and isinstance(intent_value, dict):
            intent_value = intent_value.get("value")

        if intent_value:
            anatomy_data["intent"] = intent_value

        anatomy = instance.context.data['anatomy']

        # Find the representations to transfer amongst the files
        # Each should be a single representation (as such, a single extension)
        representations = []
        destination_list = []

        orig_transfers = []
        if 'transfers' not in instance.data:
            instance.data['transfers'] = []
        else:
            orig_transfers = list(instance.data['transfers'])

        template_name = self.template_name_from_instance(instance)

        published_representations = {}
        for idx, repre in enumerate(instance.data["representations"]):
            # reset transfers for next representation
            # instance.data['transfers'] is used as a global variable
            # in current codebase
            instance.data['transfers'] = list(orig_transfers)

            if "delete" in repre.get("tags", []):
                continue

            published_files = []

            # create template data for Anatomy
            template_data = copy.deepcopy(anatomy_data)
            if intent_value is not None:
                template_data["intent"] = intent_value

            resolution_width = repre.get("resolutionWidth")
            resolution_height = repre.get("resolutionHeight")
            fps = instance.data.get("fps")

            if resolution_width:
                template_data["resolution_width"] = resolution_width
            if resolution_width:
                template_data["resolution_height"] = resolution_height
            if resolution_width:
                template_data["fps"] = fps

            files = repre['files']
            if repre.get('stagingDir'):
                stagingdir = repre['stagingDir']

            if repre.get("outputName"):
                template_data["output"] = repre['outputName']

            template = os.path.normpath(
                anatomy.templates[template_name]["path"])

            sequence_repre = isinstance(files, list)
            repre_context = None
            if sequence_repre:
                self.log.debug(
                    "files: {}".format(files))
                src_collections, remainder = clique.assemble(files)
                self.log.debug(
                    "src_tail_collections: {}".format(str(src_collections)))
                src_collection = src_collections[0]

                # Assert that each member has identical suffix
                src_head = src_collection.format("{head}")
                src_tail = src_collection.format("{tail}")

                # fix dst_padding
                valid_files = [x for x in files if src_collection.match(x)]
                padd_len = len(
                    valid_files[0].replace(src_head, "").replace(src_tail, "")
                )
                src_padding_exp = "%0{}d".format(padd_len)

                test_dest_files = list()
                for i in [1, 2]:
                    template_data["representation"] = repre['ext']
                    template_data["frame"] = src_padding_exp % i
                    anatomy_filled = anatomy.format(template_data)
                    template_filled = anatomy_filled[template_name]["path"]
                    if repre_context is None:
                        repre_context = template_filled.used_values
                    test_dest_files.append(
                        os.path.normpath(template_filled)
                    )
                template_data["frame"] = repre_context["frame"]

                self.log.debug(
                    "test_dest_files: {}".format(str(test_dest_files)))

                dst_collections, remainder = clique.assemble(test_dest_files)
                dst_collection = dst_collections[0]
                dst_head = dst_collection.format("{head}")
                dst_tail = dst_collection.format("{tail}")

                index_frame_start = None

                if repre.get("frameStart") is not None:
                    frame_start_padding = int(
                        anatomy.templates["render"].get(
                            "frame_padding",
                            anatomy.templates["render"].get("padding")
                        )
                    )

                    index_frame_start = int(repre.get("frameStart"))

                # exception for slate workflow
                if index_frame_start and "slate" in instance.data["families"]:
                    index_frame_start -= 1

                dst_padding_exp = src_padding_exp
                dst_start_frame = None
                for i in src_collection.indexes:
                    # TODO 1.) do not count padding in each index iteration
                    # 2.) do not count dst_padding from src_padding before
                    #   index_frame_start check
                    src_padding = src_padding_exp % i

                    src_file_name = "{0}{1}{2}".format(
                        src_head, src_padding, src_tail)

                    dst_padding = src_padding_exp % i

                    if index_frame_start is not None:
                        dst_padding_exp = "%0{}d".format(frame_start_padding)
                        dst_padding = dst_padding_exp % index_frame_start
                        index_frame_start += 1

                    dst = "{0}{1}{2}".format(
                        dst_head,
                        dst_padding,
                        dst_tail).replace("..", ".")

                    self.log.debug("destination: `{}`".format(dst))
                    src = os.path.join(stagingdir, src_file_name)

                    self.log.debug("source: {}".format(src))
                    instance.data["transfers"].append([src, dst])

                    published_files.append(dst)

                    # for adding first frame into db
                    if not dst_start_frame:
                        dst_start_frame = dst_padding

                # Store used frame value to template data
                template_data["frame"] = dst_start_frame
                dst = "{0}{1}{2}".format(
                    dst_head,
                    dst_start_frame,
                    dst_tail
                ).replace("..", ".")
                repre['published_path'] = dst

            else:
                # Single file
                #  _______
                # |      |\
                # |       |
                # |       |
                # |       |
                # |_______|
                #
                template_data.pop("frame", None)
                fname = files
                assert not os.path.isabs(fname), (
                    "Given file name is a full path"
                )

                template_data["representation"] = repre['ext']

                src = os.path.join(stagingdir, fname)
                anatomy_filled = anatomy.format(template_data)
                template_filled = anatomy_filled[template_name]["path"]
                repre_context = template_filled.used_values
                dst = os.path.normpath(template_filled).replace("..", ".")

                instance.data["transfers"].append([src, dst])

                published_files.append(dst)
                repre['published_path'] = dst
                self.log.debug("__ dst: {}".format(dst))

            repre["publishedFiles"] = published_files

            for key in self.db_representation_context_keys:
                value = template_data.get(key)
                if not value:
                    continue
                repre_context[key] = template_data[key]

            # Use previous representation's id if there are any
            repre_id = None
            repre_name_low = repre["name"].lower()
            for _repre in existing_repres:
                # NOTE should we check lowered names?
                if repre_name_low == _repre["name"]:
                    repre_id = _repre["orig_id"]
                    break

            # Create new id if existing representations does not match
            if repre_id is None:
                repre_id = io.ObjectId()

            data = repre.get("data") or {}
            data.update({'path': dst, 'template': template})
            representation = {
                "_id": repre_id,
                "schema": "pype:representation-2.0",
                "type": "representation",
                "parent": version_id,
                "name": repre['name'],
                "data": data,
                "dependencies": instance.data.get("dependencies", "").split(),

                # Imprint shortcut to context
                # for performance reasons.
                "context": repre_context
            }

            if repre.get("outputName"):
                representation["context"]["output"] = repre['outputName']

            if sequence_repre and repre.get("frameStart"):
                representation['context']['frame'] = (
                    dst_padding_exp % int(repre.get("frameStart"))
                )

            # any file that should be physically copied is expected in
            # 'transfers' or 'hardlinks'
            if instance.data.get('transfers', False) or \
               instance.data.get('hardlinks', False):
                # could throw exception, will be caught in 'process'
                # all integration to DB is being done together lower,
                # so no rollback needed
                self.log.debug("Integrating source files to destination ...")
                self.integrated_file_sizes.update(self.integrate(instance))
                self.log.debug("Integrated files {}".
                               format(self.integrated_file_sizes))

            # get 'files' info for representation and all attached resources
            self.log.debug("Preparing files information ...")
            representation["files"] = self.get_files_info(
                                           instance,
                                           self.integrated_file_sizes)

            self.log.debug("__ representation: {}".format(representation))
            destination_list.append(dst)
            self.log.debug("__ destination_list: {}".format(destination_list))
            instance.data['destination_list'] = destination_list
            representations.append(representation)
            published_representations[repre_id] = {
                "representation": representation,
                "anatomy_data": template_data,
                "published_files": published_files
            }
            self.log.debug("__ representations: {}".format(representations))

        # Remove old representations if there are any (before insertion of new)
        if existing_repres:
            repre_ids_to_remove = []
            for repre in existing_repres:
                repre_ids_to_remove.append(repre["_id"])
            io.delete_many({"_id": {"$in": repre_ids_to_remove}})

        self.log.debug("__ representations: {}".format(representations))
        for rep in instance.data["representations"]:
            self.log.debug("__ represNAME: {}".format(rep['name']))
            self.log.debug("__ represPATH: {}".format(rep['published_path']))
        io.insert_many(representations)
        instance.data["published_representations"] = (
            published_representations
        )
        # self.log.debug("Representation: {}".format(representations))
        self.log.info("Registered {} items".format(len(representations)))

    def integrate(self, instance):
        """ Move the files.

            Through `instance.data["transfers"]`

            Args:
                instance: the instance to integrate
            Returns:
                integrated_file_sizes: dictionary of destination file url and
                its size in bytes
        """
        # store destination url and size for reporting and rollback
        integrated_file_sizes = {}
        transfers = list(instance.data.get("transfers", list()))
        for src, dest in transfers:
            if os.path.normpath(src) != os.path.normpath(dest):
                dest = self.get_dest_temp_url(dest)
                self.copy_file(src, dest)
                # TODO needs to be updated during site implementation
                integrated_file_sizes[dest] = os.path.getsize(dest)

        # Produce hardlinked copies
        # Note: hardlink can only be produced between two files on the same
        # server/disk and editing one of the two will edit both files at once.
        # As such it is recommended to only make hardlinks between static files
        # to ensure publishes remain safe and non-edited.
        hardlinks = instance.data.get("hardlinks", list())
        for src, dest in hardlinks:
            dest = self.get_dest_temp_url(dest)
            self.log.debug("Hardlinking file ... {} -> {}".format(src, dest))
            if not os.path.exists(dest):
                self.hardlink_file(src, dest)

            # TODO needs to be updated during site implementation
            integrated_file_sizes[dest] = os.path.getsize(dest)

        return integrated_file_sizes

    def copy_file(self, src, dst):
        """ Copy given source to destination

        Arguments:
            src (str): the source file which needs to be copied
            dst (str): the destination of the sourc file
        Returns:
            None
        """
        src = os.path.normpath(src)
        dst = os.path.normpath(dst)
        self.log.debug("Copying file ... {} -> {}".format(src, dst))
        dirname = os.path.dirname(dst)
        try:
            os.makedirs(dirname)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                self.log.critical("An unexpected error occurred.")
                six.reraise(*sys.exc_info())

        # copy file with speedcopy and check if size of files are simetrical
        while True:
            import shutil
            try:
                copyfile(src, dst)
            except shutil.SameFileError:
                self.log.critical("files are the same {} to {}".format(src,
                                                                       dst))
                os.remove(dst)
                try:
                    shutil.copyfile(src, dst)
                    self.log.debug("Copying files with shutil...")
                except OSError as e:
                    self.log.critical("Cannot copy {} to {}".format(src, dst))
                    self.log.critical(e)
                    six.reraise(*sys.exc_info())
            if str(getsize(src)) in str(getsize(dst)):
                break

    def hardlink_file(self, src, dst):
        dirname = os.path.dirname(dst)

        try:
            os.makedirs(dirname)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                self.log.critical("An unexpected error occurred.")
                six.reraise(*sys.exc_info())

        filelink.create(src, dst, filelink.HARDLINK)

    def get_subset(self, asset, instance):
        subset_name = instance.data["subset"]
        subset = io.find_one({
            "type": "subset",
            "parent": asset["_id"],
            "name": subset_name
        })

        if subset is None:
            self.log.info("Subset '%s' not found, creating ..." % subset_name)
            self.log.debug("families.  %s" % instance.data.get('families'))
            self.log.debug(
                "families.  %s" % type(instance.data.get('families')))

            _id = io.insert_one({
                "schema": "pype:subset-3.0",
                "type": "subset",
                "name": subset_name,
                "data": {
                    "families": instance.data.get("families", [])
                },
                "parent": asset["_id"]
            }).inserted_id

            subset = io.find_one({"_id": _id})

        # add group if available
        if instance.data.get("subsetGroup"):
            io.update_many({
                'type': 'subset',
                '_id': io.ObjectId(subset["_id"])
            }, {'$set': {'data.subsetGroup':
                instance.data.get('subsetGroup')}}
            )

        # Update families on subset.
        families = [instance.data["family"]]
        families.extend(instance.data.get("families", []))
        io.update_many(
            {"type": "subset", "_id": io.ObjectId(subset["_id"])},
            {"$set": {"data.families": families}}
        )

        return subset

    def create_version(self, subset, version_number, data=None):
        """ Copy given source to destination

        Args:
            subset (dict): the registered subset of the asset
            version_number (int): the version number

        Returns:
            dict: collection of data to create a version
        """

        return {"schema": "pype:version-3.0",
                "type": "version",
                "parent": subset["_id"],
                "name": version_number,
                "data": data}

    def create_version_data(self, context, instance):
        """Create the data collection for the version

        Args:
            context: the current context
            instance: the current instance being published

        Returns:
            dict: the required information with instance.data as key
        """

        families = []
        current_families = instance.data.get("families", list())
        instance_family = instance.data.get("family", None)

        if instance_family is not None:
            families.append(instance_family)
        families += current_families

        # create relative source path for DB
        if "source" in instance.data:
            source = instance.data["source"]
        else:
            source = context.data["currentFile"]
            anatomy = instance.context.data["anatomy"]
            source = self.get_rootless_path(anatomy, source)

        self.log.debug("Source: {}".format(source))
        version_data = {
            "families": families,
            "time": context.data["time"],
            "author": context.data["user"],
            "source": source,
            "comment": context.data.get("comment"),
            "machine": context.data.get("machine"),
            "fps": context.data.get(
                "fps", instance.data.get("fps")
            )
        }

        intent_value = instance.context.data.get("intent")
        if intent_value and isinstance(intent_value, dict):
            intent_value = intent_value.get("value")

        if intent_value:
            version_data["intent"] = intent_value

        # Include optional data if present in
        optionals = [
            "frameStart", "frameEnd", "step", "handles",
            "handleEnd", "handleStart", "sourceHashes"
        ]
        for key in optionals:
            if key in instance.data:
                version_data[key] = instance.data[key]

        return version_data

    def main_family_from_instance(self, instance):
        """Returns main family of entered instance."""
        family = instance.data.get("family")
        if not family:
            family = instance.data["families"][0]
        return family

    def template_name_from_instance(self, instance):
        template_name = self.default_template_name
        if not self.template_name_profiles:
            self.log.debug((
                "Template name profiles are not set."
                " Using default \"{}\""
            ).format(template_name))
            return template_name

        # Task name from session?
        task_name = io.Session.get("AVALON_TASK")
        family = self.main_family_from_instance(instance)

        matching_profiles = {}
        highest_value = -1
        self.log.info(self.template_name_profiles)
        for name, filters in self.template_name_profiles.items():
            value = 0
            families = filters.get("families")
            if families:
                if family not in families:
                    continue
                value += 1

            tasks = filters.get("tasks")
            if tasks:
                if task_name not in tasks:
                    continue
                value += 1

            if value > highest_value:
                matching_profiles = {}
                highest_value = value

            if value == highest_value:
                matching_profiles[name] = filters

        if len(matching_profiles) == 1:
            template_name = tuple(matching_profiles.keys())[0]
            self.log.debug(
                "Using template name \"{}\".".format(template_name)
            )

        elif len(matching_profiles) > 1:
            template_name = tuple(matching_profiles.keys())[0]
            self.log.warning((
                "More than one template profiles matched"
                " Family \"{}\" and Task: \"{}\"."
                " Using first template name in row \"{}\"."
            ).format(family, task_name, template_name))

        else:
            self.log.debug((
                "None of template profiles matched"
                " Family \"{}\" and Task: \"{}\"."
                " Using default template name \"{}\""
            ).format(family, task_name, template_name))

        return template_name

    def get_rootless_path(self, anatomy, path):
        """  Returns, if possible, path without absolute portion from host
             (eg. 'c:\' or '/opt/..')
             This information is host dependent and shouldn't be captured.
             Example:
                 'c:/projects/MyProject1/Assets/publish...' >
                 '{root}/MyProject1/Assets...'

        Args:
                anatomy: anatomy part from instance
                path: path (absolute)
        Returns:
                path: modified path if possible, or unmodified path
                + warning logged
        """
        success, rootless_path = (
            anatomy.find_root_template_from_path(path)
        )
        if success:
            path = rootless_path
        else:
            self.log.warning((
                              "Could not find root path for remapping \"{}\"."
                              " This may cause issues on farm."
                              ).format(path))
        return path

    def get_files_info(self, instance, integrated_file_sizes):
        """ Prepare 'files' portion for attached resources and main asset.
            Combining records from 'transfers' and 'hardlinks' parts from
            instance.
            All attached resources should be added, currently without
            Context info.

        Arguments:
            instance: the current instance being published
            integrated_file_sizes: dictionary of destination path (absolute)
            and its file size
        Returns:
            output_resources: array of dictionaries to be added to 'files' key
            in representation
        """
        resources = list(instance.data.get("transfers", []))
        resources.extend(list(instance.data.get("hardlinks", [])))

        self.log.debug("get_resource_files_info.resources:{}".
                       format(resources))

        output_resources = []
        anatomy = instance.context.data["anatomy"]
        for _src, dest in resources:
            path = self.get_rootless_path(anatomy, dest)
            dest = self.get_dest_temp_url(dest)
            file_hash = pype.api.source_hash(dest)
            if self.TMP_FILE_EXT and \
               ',{}'.format(self.TMP_FILE_EXT) in file_hash:
                file_hash = file_hash.replace(',{}'.format(self.TMP_FILE_EXT),
                                              '')

            file_info = self.prepare_file_info(path,
                                               integrated_file_sizes[dest],
                                               file_hash)
            output_resources.append(file_info)

        return output_resources

    def get_dest_temp_url(self, dest):
        """ Enhance destination path with TMP_FILE_EXT to denote temporary
            file.
            Temporary files will be renamed after successful registration
            into DB and full copy to destination

        Arguments:
            dest: destination url of published file (absolute)
        Returns:
            dest: destination path + '.TMP_FILE_EXT'
        """
        if self.TMP_FILE_EXT and '.{}'.format(self.TMP_FILE_EXT) not in dest:
            dest += '.{}'.format(self.TMP_FILE_EXT)
        return dest

    def prepare_file_info(self, path, size=None, file_hash=None, sites=None):
        """ Prepare information for one file (asset or resource)

        Arguments:
            path: destination url of published file (rootless)
            size(optional): size of file in bytes
            file_hash(optional): hash of file for synchronization validation
            sites(optional): array of published locations,
                            ['studio': {'created_dt':date}] by default
                                keys expected ['studio', 'site1', 'gdrive1']
        Returns:
            rec: dictionary with filled info
        """

        rec = {
            "_id": io.ObjectId(),
            "path": path
        }
        if size:
            rec["size"] = size

        if file_hash:
            rec["hash"] = file_hash

        if sites:
            rec["sites"] = sites
        else:
            meta = {"created_dt": datetime.now()}
            rec["sites"] = {"studio": meta}

        return rec

    def handle_destination_files(self, integrated_file_sizes, mode):
        """ Clean destination files
            Called when error happened during integrating to DB or to disk
            OR called to rename uploaded files from temporary name to final to
            highlight publishing in progress/broken
            Used to clean unwanted files

        Arguments:
            integrated_file_sizes: dictionary, file urls as keys, size as value
            mode: 'remove' - clean files,
                  'finalize' - rename files,
                               remove TMP_FILE_EXT suffix denoting temp file
        """
        if integrated_file_sizes:
            for file_url, _file_size in integrated_file_sizes.items():
                if not os.path.exists(file_url):
                    self.log.debug(
                        "File {} was not found.".format(file_url)
                    )
                    continue

                try:
                    if mode == 'remove':
                        self.log.debug("Removing file {}".format(file_url))
                        os.remove(file_url)
                    if mode == 'finalize':
                        new_name = re.sub(
                            r'\.{}$'.format(self.TMP_FILE_EXT),
                            '',
                            file_url
                        )

                        if os.path.exists(new_name):
                            self.log.debug(
                                "Overwriting file {} to {}".format(
                                    file_url, new_name
                                )
                            )
                            shutil.copy(file_url, new_name)
                        else:
                            self.log.debug(
                                "Renaming file {} to {}".format(
                                    file_url, new_name
                                )
                            )
                            os.rename(file_url, new_name)
                except OSError:
                    self.log.error("Cannot {} file {}".format(mode, file_url),
                                   exc_info=True)
                    six.reraise(*sys.exc_info())
