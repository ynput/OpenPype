import os
import logging
import shutil

import errno
import pyblish.api
from avalon import api, io
from avalon.vendor import filelink


log = logging.getLogger(__name__)


class IntegrateAsset(pyblish.api.InstancePlugin):
    """Resolve any dependency issies

    This plug-in resolves any paths which, if not updated might break
    the published file.

    The order of families is important, when working with lookdev you want to
    first publish the texture, update the texture paths in the nodes and then
    publish the shading network. Same goes for file dependent assets.
    """

    label = "Integrate Asset"
    order = pyblish.api.IntegratorOrder
    families = ["assembly"]
    exclude_families = ["clip"]

    def process(self, instance):
        if [ef for ef in self.exclude_families
                if instance.data["family"] in ef]:
            return

        self.register(instance)

        self.log.info("Integrating Asset in to the database ...")
        if instance.data.get('transfer', True):
            self.integrate(instance)

    def register(self, instance):
        # Required environment variables
        PROJECT = api.Session["AVALON_PROJECT"]
        ASSET = instance.data.get("asset") or api.Session["AVALON_ASSET"]
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
        assert all(result["success"] for result in context.data["results"]), (
            "Atomicity not held, aborting.")

        # Assemble
        #
        #       |
        #       v
        #  --->   <----
        #       ^
        #       |
        #
        stagingdir = instance.data.get("stagingDir")
        assert stagingdir, ("Incomplete instance \"%s\": "
                            "Missing reference to staging area." % instance)

        # extra check if stagingDir actually exists and is available

        self.log.debug("Establishing staging directory @ %s" % stagingdir)

        # Ensure at least one file is set up for transfer in staging dir.
        files = instance.data.get("files", [])
        assert files, "Instance has no files to transfer"
        assert isinstance(files, (list, tuple)), (
            "Instance 'files' must be a list, got: {0}".format(files)
        )

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

        self.log.info("Verifying version from assumed destination")

        assumed_data = instance.data["assumedTemplateData"]
        assumed_version = assumed_data["version"]
        if assumed_version != next_version:
            raise AttributeError("Assumed version 'v{0:03d}' does not match"
                                 "next version in database "
                                 "('v{1:03d}')".format(assumed_version,
                                                       next_version))

        self.log.debug("Next version: v{0:03d}".format(next_version))

        version_data = self.create_version_data(context, instance)
        version = self.create_version(subset=subset,
                                      version_number=next_version,
                                      locations=[LOCATION],
                                      data=version_data)

        self.log.debug("Creating version ...")
        version_id = io.insert_one(version).inserted_id

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

        template_data = {"root": root,
                         "project": {"name": PROJECT,
                                     "code": project['data']['code']},
                         "silo": asset['silo'],
                         "asset": ASSET,
                         "family": instance.data['family'],
                         "subset": subset["name"],
                         "version": int(version["name"]),
                         "hierarchy": hierarchy}

        # template_publish = project["config"]["template"]["publish"]
        anatomy = instance.context.data['anatomy']

        # Find the representations to transfer amongst the files
        # Each should be a single representation (as such, a single extension)
        representations = []
        destination_list = []
        if 'transfers' not in instance.data:
            instance.data['transfers'] = []

        for files in instance.data["files"]:

            # Collection
            #   _______
            #  |______|\
            # |      |\|
            # |       ||
            # |       ||
            # |       ||
            # |_______|
            #

            if isinstance(files, list):
                collection = files
                # Assert that each member has identical suffix
                _, ext = os.path.splitext(collection[0])
                assert all(ext == os.path.splitext(name)[1]
                           for name in collection), (
                    "Files had varying suffixes, this is a bug"
                )

                assert not any(os.path.isabs(name) for name in collection)

                template_data["representation"] = ext[1:]

                for fname in collection:

                    src = os.path.join(stagingdir, fname)
                    anatomy_filled = anatomy.format(template_data)
                    dst = anatomy_filled["publish"]["path"]

                    instance.data["transfers"].append([src, dst])
                    template = anatomy.templates["publish"]["path"]

            else:
                # Single file
                #  _______
                # |      |\
                # |       |
                # |       |
                # |       |
                # |_______|
                #
                fname = files
                assert not os.path.isabs(fname), (
                    "Given file name is a full path"
                )
                _, ext = os.path.splitext(fname)

                template_data["representation"] = ext[1:]

                src = os.path.join(stagingdir, fname)
                anatomy_filled = anatomy.format(template_data)
                dst = anatomy_filled["publish"]["path"]

                instance.data["transfers"].append([src, dst])
                template = anatomy.templates["publish"]["path"]

            representation = {
                "schema": "pype:representation-2.0",
                "type": "representation",
                "parent": version_id,
                "name": ext[1:],
                "data": {'path': dst, 'template': template},
                "dependencies": instance.data.get("dependencies", "").split(),

                # Imprint shortcut to context
                # for performance reasons.
                "context": {
                    "root": root,
                    "project": {"name": PROJECT,
                                "code": project['data']['code']},
                    'task': api.Session["AVALON_TASK"],
                    "silo": asset['silo'],
                    "asset": ASSET,
                    "family": instance.data['family'],
                    "subset": subset["name"],
                    "version": version["name"],
                    "hierarchy": hierarchy,
                    "representation": ext[1:]
                }
            }

            destination_list.append(dst)
            instance.data['destination_list'] = destination_list
            representations.append(representation)

        self.log.info("Registering {} items".format(len(representations)))

        io.insert_many(representations)

    def integrate(self, instance):
        """Move the files

        Through `instance.data["transfers"]`

        Args:
            instance: the instance to integrate
        """

        transfers = instance.data.get("transfers", list())

        for src, dest in transfers:
            self.log.info("Copying file .. {} -> {}".format(src, dest))
            self.copy_file(src, dest)

        # Produce hardlinked copies
        # Note: hardlink can only be produced between two files on the same
        # server/disk and editing one of the two will edit both files at once.
        # As such it is recommended to only make hardlinks between static files
        # to ensure publishes remain safe and non-edited.
        hardlinks = instance.data.get("hardlinks", list())
        for src, dest in hardlinks:
            self.log.info("Hardlinking file .. {} -> {}".format(src, dest))
            self.hardlink_file(src, dest)

    def copy_file(self, src, dst):
        """ Copy given source to destination

        Arguments:
            src (str): the source file which needs to be copied
            dst (str): the destination of the sourc file
        Returns:
            None
        """

        dirname = os.path.dirname(dst)
        try:
            os.makedirs(dirname)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                self.log.critical("An unexpected error occurred.")
                raise

        shutil.copy(src, dst)

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

            _id = io.insert_one({
                "schema": "avalon-core:subset-2.0",
                "type": "subset",
                "name": subset_name,
                "data": {},
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

        return {"schema": "avalon-core:version-2.0",
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
            "frameStart", "frameEnd", "step", "handles", "sourceHashes"
        ]
        for key in optionals:
            if key in instance.data:
                version_data[key] = instance.data[key]

        return version_data
