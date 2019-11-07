import os
from os.path import getsize
import logging
import speedcopy
import clique
import errno
import pyblish.api
from avalon import api, io
from avalon.vendor import filelink

log = logging.getLogger(__name__)


class IntegrateAssetNew(pyblish.api.InstancePlugin):
    """Resolve any dependency issius

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
                "render",
                "rendersetup",
                "rig",
                "plate",
                "look",
                "lut",
                "audio",
                "yetiRig",
                "yeticache"
                ]
    exclude_families = ["clip"]

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
        PROJECT = api.Session["AVALON_PROJECT"]
        ASSET = instance.data.get("asset") or api.Session["AVALON_ASSET"]
        TASK = instance.data.get("task") or api.Session["AVALON_TASK"]
        LOCATION = api.Session["AVALON_LOCATION"]

        context = instance.context
        # Atomicity
        #
        # Guarantee atomic publishes - each asset contains
        # an identical set of members.
        #     __
        #    /     o
        #   /       \
        #  |    o    |
        #   \       /
        #    o   __/
        #
        # for result in context.data["results"]:
        #     if not result["success"]:
        #         self.log.debug(result)
        #         exc_type, exc_value, exc_traceback = result["error_info"]
        #         extracted_traceback = traceback.extract_tb(exc_traceback)[-1]
        #         self.log.debug(
        #             "Error at line {}: \"{}\"".format(
        #                 extracted_traceback[1], result["error"]
        #             )
        #         )
        # assert all(result["success"] for result in context.data["results"]),(
        #     "Atomicity not held, aborting.")

        # Assemble
        #
        #       |
        #       v
        #  --->   <----
        #       ^
        #       |
        #
        stagingdir = instance.data.get("stagingDir")
        if not stagingdir:
            self.log.info('''{} is missing reference to staging
                            directory Will try to get it from
                            representation'''.format(instance))

        # extra check if stagingDir actually exists and is available

        self.log.debug("Establishing staging directory @ %s" % stagingdir)

        # Ensure at least one file is set up for transfer in staging dir.
        repres = instance.data.get("representations", None)
        assert repres, "Instance has no files to transfer"
        assert isinstance(repres, (list, tuple)), (
            "Instance 'files' must be a list, got: {0}".format(repres)
        )

        # FIXME: io is not initialized at this point for shell host
        io.install()
        project = io.find_one({"type": "project"})

        asset = io.find_one({"type": "asset",
                             "name": ASSET,
                             "parent": project["_id"]})

        assert all([project, asset]), ("Could not find current project or "
                                       "asset '%s'" % ASSET)

        subset = self.get_subset(asset, instance)

        # get next version
        latest_version = io.find_one({"type": "version",
                                      "parent": subset["_id"]},
                                     {"name": True},
                                     sort=[("name", -1)])

        next_version = 1
        if latest_version is not None:
            next_version += latest_version["name"]

        if instance.data.get('version'):
            next_version = int(instance.data.get('version'))

        # self.log.info("Verifying version from assumed destination")

        # assumed_data = instance.data["assumedTemplateData"]
        # assumed_version = assumed_data["version"]
        # if assumed_version != next_version:
        #     raise AttributeError("Assumed version 'v{0:03d}' does not match"
        #                          "next version in database "
        #                          "('v{1:03d}')".format(assumed_version,
        #                                                next_version))

        self.log.debug("Next version: v{0:03d}".format(next_version))

        version_data = self.create_version_data(context, instance)

        version_data_instance = instance.data.get('versionData')

        if version_data_instance:
            version_data.update(version_data_instance)

        version = self.create_version(subset=subset,
                                      version_number=next_version,
                                      locations=[LOCATION],
                                      data=version_data)

        self.log.debug("Creating version ...")
        existing_version = io.find_one({
            'type': 'version',
            'parent': subset["_id"],
            'name': next_version
        })
        if existing_version is None:
            version_id = io.insert_one(version).inserted_id
        else:
            io.update_many({
                'type': 'version',
                'parent': subset["_id"],
                'name': next_version
            }, {'$set': version}
            )
            version_id = existing_version['_id']
        instance.data['version'] = version['name']

        # Write to disk
        #          _
        #         | |
        #        _| |_
        #    ____\   /
        #   |\    \ / \
        #   \ \    v   \
        #    \ \________.
        #     \|________|
        #
        root = api.registered_root()
        hierarchy = ""
        parents = io.find_one({
            "type": 'asset',
            "name": ASSET
        })['data']['parents']
        if parents and len(parents) > 0:
            # hierarchy = os.path.sep.join(hierarchy)
            hierarchy = os.path.join(*parents)

        anatomy = instance.context.data['anatomy']

        # Find the representations to transfer amongst the files
        # Each should be a single representation (as such, a single extension)
        representations = []
        destination_list = []
        template_name = 'publish'
        if 'transfers' not in instance.data:
            instance.data['transfers'] = []

        for idx, repre in enumerate(instance.data["representations"]):

            # Collection
            #   _______
            #  |______|\
            # |      |\|
            # |       ||
            # |       ||
            # |       ||
            # |_______|
            #
            # create template data for Anatomy
            template_data = {"root": root,
                             "project": {"name": PROJECT,
                                         "code": project['data']['code']},
                             "silo": asset.get('silo'),
                             "task": TASK,
                             "asset": ASSET,
                             "family": instance.data['family'],
                             "subset": subset["name"],
                             "version": int(version["name"]),
                             "hierarchy": hierarchy}

            files = repre['files']
            if repre.get('stagingDir'):
                stagingdir = repre['stagingDir']
            if repre.get('anatomy_template'):
                template_name = repre['anatomy_template']
            template = os.path.normpath(
                anatomy.templates[template_name]["path"])

            sequence_repre = isinstance(files, list)

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

                    test_dest_files.append(
                        os.path.normpath(
                            anatomy_filled[template_name]["path"])
                    )

                self.log.debug(
                    "test_dest_files: {}".format(str(test_dest_files)))

                dst_collections, remainder = clique.assemble(test_dest_files)
                dst_collection = dst_collections[0]
                dst_head = dst_collection.format("{head}")
                dst_tail = dst_collection.format("{tail}")

                index_frame_start = None

                if repre.get("frameStart"):
                    frame_start_padding = len(str(
                        repre.get("frameEnd")))
                    index_frame_start = int(repre.get("frameStart"))

                dst_padding_exp = src_padding_exp
                dst_start_frame = None
                for i in src_collection.indexes:
                    src_padding = src_padding_exp % i

                    # for adding first frame into db
                    if not dst_start_frame:
                        dst_start_frame = src_padding

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

                dst = "{0}{1}{2}".format(
                    dst_head,
                    dst_start_frame,
                    dst_tail).replace("..", ".")
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

                if repre.get("outputName"):
                    template_data["output"] = repre['outputName']

                src = os.path.join(stagingdir, fname)
                anatomy_filled = anatomy.format(template_data)
                dst = os.path.normpath(
                    anatomy_filled[template_name]["path"]).replace("..", ".")

                instance.data["transfers"].append([src, dst])

                repre['published_path'] = dst
                self.log.debug("__ dst: {}".format(dst))

            representation = {
                "schema": "pype:representation-2.0",
                "type": "representation",
                "parent": version_id,
                "name": repre['name'],
                "data": {'path': dst, 'template': template},
                "dependencies": instance.data.get("dependencies", "").split(),

                # Imprint shortcut to context
                # for performance reasons.
                "context": {
                    "root": root,
                    "project": {"name": PROJECT,
                                "code": project['data']['code']},
                    'task': TASK,
                    "silo": asset.get('silo'),
                    "asset": ASSET,
                    "family": instance.data['family'],
                    "subset": subset["name"],
                    "version": version["name"],
                    "hierarchy": hierarchy,
                    "representation": repre['ext']
                }
            }

            if sequence_repre and repre.get("frameStart"):
                representation['context']['frame'] = repre.get("frameStart")

            self.log.debug("__ representation: {}".format(representation))
            destination_list.append(dst)
            self.log.debug("__ destination_list: {}".format(destination_list))
            instance.data['destination_list'] = destination_list
            representations.append(representation)
            self.log.debug("__ representations: {}".format(representations))

        self.log.debug("__ representations: {}".format(representations))
        for rep in instance.data["representations"]:
            self.log.debug("__ represNAME: {}".format(rep['name']))
            self.log.debug("__ represPATH: {}".format(rep['published_path']))
        io.insert_many(representations)
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
            speedcopy.copyfile(src, dst)
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
                raise

        filelink.create(src, dst, filelink.HARDLINK)

    def get_subset(self, asset, instance):

        subset = io.find_one({"type": "subset",
                              "parent": asset["_id"],
                              "name": instance.data["subset"]})

        if subset is None:
            subset_name = instance.data["subset"]
            self.log.info("Subset '%s' not found, creating.." % subset_name)
            self.log.debug("families.  %s" % instance.data.get('families'))
            self.log.debug("families.  %s" % type(instance.data.get('families')))

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

        return subset

    def create_version(self, subset, version_number, locations, data=None):
        """ Copy given source to destination

        Args:
            subset (dict): the registered subset of the asset
            version_number (int): the version number
            locations (list): the currently registered locations

        Returns:
            dict: collection of data to create a version
        """
        # Imprint currently registered location
        version_locations = [location for location in locations if
                             location is not None]

        return {"schema": "pype:version-3.0",
                "type": "version",
                "parent": subset["_id"],
                "name": version_number,
                "locations": version_locations,
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
                        "fps": context.data.get("fps")}

        # Include optional data if present in
        optionals = [
            "frameStart", "frameEnd", "step", "handles",
            "handleEnd", "handleStart", "sourceHashes"
        ]
        for key in optionals:
            if key in instance.data:
                version_data[key] = instance.data[key]

        return version_data
