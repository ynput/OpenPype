import pyblish.api
import logging
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
