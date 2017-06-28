import os
import errno
import shutil
from pprint import pformat

import pyblish.api
from avalon import api, io


class IntegrateMindbenderAsset(pyblish.api.InstancePlugin):
    """Write to files and metadata

    This plug-in exposes your data to others by encapsulating it
    into a new version.

    Schema:
        Data is written in the following format.
         ____________________
        |                    |
        | version            |
        |  ________________  |
        | |                | |
        | | representation | |
        | |________________| |
        | |                | |
        | | ...            | |
        | |________________| |
        |____________________|

    """

    label = "Integrate Asset"
    order = pyblish.api.IntegratorOrder
    families = [
        "colorbleed.model",
        "colorbleed.rig",
        "colorbleed.animation",
        "colorbleed.camera",
        "colorbleed.lookdev",
        "colorbleed.historyLookdev",
        "colorbleed.group",
        "colorbleed.pointcache"
    ]

    def process(self, instance):
        # Required environment variables
        PROJECT = os.environ["AVALON_PROJECT"]
        ASSET = instance.data.get("asset") or os.environ["AVALON_ASSET"]
        SILO = os.environ["AVALON_SILO"]
        LOCATION = os.getenv("AVALON_LOCATION")

        # todo(marcus): avoid hardcoding labels in the integrator
        representation_labels = {".ma": "Maya Ascii",
                                 ".source": "Original source file",
                                 ".abc": "Alembic"}

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

        self.log.debug("Establishing staging directory @ %s" % stagingdir)

        project = io.find_one({"type": "project"})
        asset = io.find_one({"name": ASSET})

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

        self.log.debug("Next version: %i" % next_version)

        version_data = self.create_version_data(context, instance)
        version = self.create_version(subset=subset,
                                      version_number=next_version,
                                      locations=[LOCATION],
                                      data=version_data)

        self.log.debug("Creating version: %s" % pformat(version))
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
        template_data = {
            "root": api.registered_root(),
            "project": PROJECT,
            "silo": SILO,
            "asset": ASSET,
            "subset": subset["name"],
            "version": version["name"],
        }

        template_publish = project["config"]["template"]["publish"]

        for fname in os.listdir(stagingdir):
            name, ext = os.path.splitext(fname)
            template_data["representation"] = ext[1:]

            src = os.path.join(stagingdir, fname)
            dst = template_publish.format(**template_data)

            # Backwards compatibility
            if fname == ".metadata.json":
                dirname = os.path.dirname(dst)
                dst = os.path.join(dirname, ".metadata.json")

            self.log.info("Copying %s -> %s" % (src, dst))

            # copy source to destination (library)
            self.copy_file(src, dst)

            representation = {
                "schema": "avalon-core:representation-2.0",
                "type": "representation",
                "parent": version_id,
                "name": ext[1:],
                "data": {"label": representation_labels.get(ext)},
                "dependencies": instance.data.get("dependencies", "").split(),

                # Imprint shortcut to context
                # for performance reasons.
                "context": {
                    "project": PROJECT,
                    "asset": ASSET,
                    "silo": SILO,
                    "subset": subset["name"],
                    "version": version["name"],
                    "representation": ext[1:]
                }
            }

            io.insert_one(representation)

        self.log.info("Successfully integrated \"%s\" to \"%s\"" % (
            instance, dst))

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

    def create_representation(self):
        pass

    def create_version(self, subset, version_number, locations, data=None):
        """ Copy given source to destination

        Arguments:
            subset (dict): the registered subset of the asset
            version_number (int): the version number
            locations (list): the currently registered locations
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
        """
        Create the data collection for th version
        Args:
            context (object): the current context
            instance(object): the current instance being published

        Returns:
            dict: the required information with instance.data as key
        """

        families = []
        current_families = instance.data.get("families", list())
        instance_family = instance.data.get("family", None)

        families += current_families
        if instance_family is not None:
            families.append(instance_family)

        # create relative source path for DB
        relative_path = os.path.relpath(context.data["currentFile"],
                                        api.registered_root())
        source = os.path.join("{root}", relative_path).replace("\\", "/")

        version_data = {"families": families,
                        "time": context.data["time"],
                        "author": context.data["user"],
                        "source": source,
                        "comment": context.data.get("comment")}

        return dict(instance.data, **version_data)

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