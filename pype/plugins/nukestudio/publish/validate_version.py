import pyblish
from avalon import io
from pype.action import get_errored_instances_from_context
import pype.api as pype

@pyblish.api.log
class RepairNukestudioVersionUp(pyblish.api.Action):
    label = "Version Up Workfile"
    on = "failed"
    icon = "wrench"

    def process(self, context, plugin):

        errored_instances = get_errored_instances_from_context(context)

        # Apply pyblish logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(errored_instances, plugin)

        if instances:
            project = context.data["activeProject"]
            path = context.data.get("currentFile")

            new_path = pype.version_up(path)

            if project:
                project.saveAs(new_path)

            self.log.info("Project workfile version was fixed")


class ValidateVersion(pyblish.api.InstancePlugin):
    """Validate clip's versions.

    """

    order = pyblish.api.ValidatorOrder
    families = ["plate"]
    label = "Validate Version"
    actions = [RepairNukestudioVersionUp]
    hosts = ["nukestudio"]

    def process(self, instance):
        version = int(instance.data.get("version", 0))
        asset_name = instance.data.get("asset", None)
        subset_name = instance.data.get("subset", None)

        assert version, "The file is missing version string! example: filename_v001.hrox `{}`"

        self.log.debug("Collected version: `{0}`".format(version))

        found_v = 0
        try:
            io.install()
            project = io.find_one({"type": "project"})

            asset = io.find_one({"type": "asset",
                                 "name": asset_name,
                                 "parent": project["_id"]})

            subset = io.find_one({"type": "subset",
                                  "parent": asset["_id"],
                                  "name": subset_name})

            version_db = io.find_one({
                'type': 'version',
                'parent': subset["_id"],
                'name': version
            }) or {}
            found_v = version_db.get("name", 0)
            self.log.debug("Found version: `{0}`".format(found_v))
        except Exception as e:
            self.log.debug("Problem to get data from database for asset `{0}` subset `{1}`. Error: `{2}`".format(asset_name, subset_name, e))

        assert (found_v != version), "Version must not be the same as in database `{0}`, Versions file: `{1}`, db: `{2}`".format(asset_name, version, found_v)
