import os
import logging

import pyblish.api
from avalon import api, io

log = logging.getLogger(__name__)


class UpdateVersion(pyblish.api.InstancePlugin):
    """Update existing subset version with new data"""

    label = "Update Subset Version"
    order = pyblish.api.IntegratorOrder
    families = ["attach-render"]

    def process(self, instance):
        # Required environment variables
        PROJECT = api.Session["AVALON_PROJECT"]
        ASSET = instance.data.get("asset") or api.Session["AVALON_ASSET"]
        TASK = instance.data.get("task") or api.Session["AVALON_TASK"]
        LOCATION = api.Session["AVALON_LOCATION"]

        context = instance.context

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

        assert instance.data.get("attachTo"), "no subset to attach to"
        for subset_to_attach in instance.data.get("attachTo"):

            subset = io.find_one({"type": "subset",
                                  "parent": asset["_id"],
                                  "name": subset_to_attach["subset"]})

            assert all([project, asset]), ("Could not find current project or "
                                           "asset '%s'" % ASSET)

            attach_version = subset_to_attach["version"]

            version_data = self.create_version_data(context, instance)

            version_data_instance = instance.data.get('versionData')

            if version_data_instance:
                version_data.update(version_data_instance)

            version = self.create_version(subset=subset,
                                          version_number=attach_version,
                                          locations=[LOCATION],
                                          data=version_data)

            self.log.debug("Creating version ...")
            existing_version = io.find_one({
                'type': 'version',
                'parent': subset["_id"],
                'name': attach_version
            })
            if existing_version is None:
                version_id = io.insert_one(version).inserted_id
            else:
                io.update_many({
                    'type': 'version',
                    'parent': subset["_id"],
                    'name': attach_version
                }, {'$set': version}
                )
                version_id = existing_version['_id']
            instance.data['version'] = version['name']

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
