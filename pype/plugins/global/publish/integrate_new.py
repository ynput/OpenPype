import os
from os.path import getsize
import logging
import sys
import copy
import clique
import errno

from pymongo import DeleteOne, InsertOne
import pyblish.api
from avalon import api, io
from avalon.vendor import filelink

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
        'anatomy_template': 'publish' or 'render', etc.
                            template from anatomy that should be used for
                            integrating this file. Only the first level can
                            be specified right now.
        "frameStart"
        "frameEnd"
        'fps'
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
                "image"
                "source",
                "assembly",
                "textures"
                "action"
                ]
    exclude_families = ["clip"]
    db_representation_context_keys = [
        "project", "asset", "task", "subset", "version", "representation",
        "family", "hierarchy", "task", "username"
    ]

    def process(self, instance):

        if [ef for ef in self.exclude_families
                if instance.data["family"] in ef]:
            return

        self.register(instance)

        self.log.info("Integrating Asset in to the database ...")
        self.log.info("instance.data: {}".format(instance.data))
        if instance.data.get('transfer', True):
            self.integrate(instance)

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
        template_name = 'publish'
        if 'transfers' not in instance.data:
            instance.data['transfers'] = []

        published_representations = {}
        for idx, repre in enumerate(instance.data["representations"]):
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
            if repre.get('anatomy_template'):
                template_name = repre['anatomy_template']
            if repre.get("outputName"):
                template_data["output"] = repre['outputName']

            template = os.path.normpath(
                anatomy.templates[template_name]["path"])

            sequence_repre = isinstance(files, list)
            repre_context = None
            if sequence_repre:
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

                self.log.debug(
                    "test_dest_files: {}".format(str(test_dest_files)))

                dst_collections, remainder = clique.assemble(test_dest_files)
                dst_collection = dst_collections[0]
                dst_head = dst_collection.format("{head}")
                dst_tail = dst_collection.format("{tail}")

                index_frame_start = None

                if repre.get("frameStart"):
                    frame_start_padding = (
                        anatomy.templates["render"]["padding"]
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

                    if index_frame_start:
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

                dst = "{0}{1}{2}".format(
                    dst_head,
                    dst_start_frame,
                    dst_tail
                ).replace("..", ".")
                repre['published_path'] = self.unc_convert(dst)

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
                repre['published_path'] = self.unc_convert(dst)
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

            representation = {
                "_id": repre_id,
                "schema": "pype:representation-2.0",
                "type": "representation",
                "parent": version_id,
                "name": repre['name'],
                "data": {'path': dst, 'template': template},
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
        """
        transfers = instance.data.get("transfers", list())

        for src, dest in transfers:
            if os.path.normpath(src) != os.path.normpath(dest):
                self.copy_file(src, dest)

        transfers = instance.data.get("transfers", list())
        for src, dest in transfers:
            self.copy_file(src, dest)

        # Produce hardlinked copies
        # Note: hardlink can only be produced between two files on the same
        # server/disk and editing one of the two will edit both files at once.
        # As such it is recommended to only make hardlinks between static files
        # to ensure publishes remain safe and non-edited.
        hardlinks = instance.data.get("hardlinks", list())
        for src, dest in hardlinks:
            self.log.debug("Hardlinking file .. {} -> {}".format(src, dest))
            self.hardlink_file(src, dest)

    def unc_convert(self, path):
        self.log.debug("> __ path: `{}`".format(path))
        drive, _path = os.path.splitdrive(path)
        self.log.debug("> __ drive, _path: `{}`, `{}`".format(drive, _path))

        if not os.path.exists(drive + "/"):
            self.log.info("Converting to unc from environments ..")

            path_replace = os.getenv("PYPE_STUDIO_PROJECTS_PATH")
            path_mount = os.getenv("PYPE_STUDIO_PROJECTS_MOUNT")

            if "/" in path_mount:
                path = path.replace(path_mount[0:-1], path_replace)
            else:
                path = path.replace(path_mount, path_replace)
        return path

    def copy_file(self, src, dst):
        """ Copy given source to destination

        Arguments:
            src (str): the source file which needs to be copied
            dst (str): the destination of the sourc file
        Returns:
            None
        """
        src = self.unc_convert(src)
        dst = self.unc_convert(dst)
        src = os.path.normpath(src)
        dst = os.path.normpath(dst)
        self.log.debug("Copying file .. {} -> {}".format(src, dst))
        dirname = os.path.dirname(dst)
        try:
            os.makedirs(dirname)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                self.log.critical("An unexpected error occurred.")
                raise

        # copy file with speedcopy and check if size of files are simetrical
        while True:
            copyfile(src, dst)
            if str(getsize(src)) in str(getsize(dst)):
                break

    def hardlink_file(self, src, dst):
        dirname = os.path.dirname(dst)

        src = self.unc_convert(src)
        dst = self.unc_convert(dst)

        try:
            os.makedirs(dirname)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                self.log.critical("An unexpected error occurred.")
                raise

        filelink.create(src, dst, filelink.HARDLINK)

    def get_subset(self, asset, instance):
        subset_name = instance.data["subset"]
        subset = io.find_one({
            "type": "subset",
            "parent": asset["_id"],
            "name": subset_name
        })

        if subset is None:
            self.log.info("Subset '%s' not found, creating.." % subset_name)
            self.log.debug("families.  %s" % instance.data.get('families'))
            self.log.debug(
                "families.  %s" % type(instance.data.get('families')))

            _id = io.insert_one({
                "schema": "pype:subset-3.0",
                "type": "subset",
                "name": subset_name,
                "data": {
                    "families": instance.data.get('families')
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

        self.log.debug("Registered root: {}".format(api.registered_root()))
        # create relative source path for DB
        try:
            source = instance.data['source']
        except KeyError:
            source = context.data["currentFile"]
            source = source.replace(os.getenv("PYPE_STUDIO_PROJECTS_MOUNT"),
                                    api.registered_root())
            relative_path = os.path.relpath(source, api.registered_root())
            source = os.path.join("{root}", relative_path).replace("\\", "/")

        self.log.debug("Source: {}".format(source))
        version_data = {"families": families,
                        "time": context.data["time"],
                        "author": context.data["user"],
                        "source": source,
                        "comment": context.data.get("comment"),
                        "machine": context.data.get("machine"),
                        "fps": context.data.get(
                            "fps", instance.data.get("fps"))}

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
