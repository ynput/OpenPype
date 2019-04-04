import os
import pyblish.api

from avalon import io, api, lib


class CollectAssumedDestination(pyblish.api.InstancePlugin):
    """Generate the assumed destination path where the file will be stored"""

    label = "Collect Assumed Destination"
    order = pyblish.api.CollectorOrder + 0.498
    exclude_families = ["clip"]

    def process(self, instance):
        """Create a destination filepath based on the current data available

        Example template:
            {root}/{project}/{silo}/{asset}/publish/{subset}/v{version:0>3}/
            {subset}.{representation}
        Args:
            instance: the instance to publish

        Returns:
            file path (str)
        """
        if [ef for ef in self.exclude_families
                if instance.data["family"] in ef]:
            return

        # get all the stuff from the database
        subset_name = instance.data["subset"]
        asset_name = instance.data["asset"]
        project_name = api.Session["AVALON_PROJECT"]

        project = io.find_one({"type": "project",
                               "name": project_name},
                              projection={"config": True, "data": True})

        template = project["config"]["template"]["publish"]
        anatomy = instance.context.data['anatomy']

        asset = io.find_one({"type": "asset",
                             "name": asset_name,
                             "parent": project["_id"]})

        assert asset, ("No asset found by the name '{}' "
                       "in project '{}'".format(asset_name, project_name))
        silo = asset['silo']

        subset = io.find_one({"type": "subset",
                              "name": subset_name,
                              "parent": asset["_id"]})

        # assume there is no version yet, we start at `1`
        version = None
        version_number = 1
        if subset is not None:
            version = io.find_one({"type": "version",
                                   "parent": subset["_id"]},
                                  sort=[("name", -1)])

        # if there is a subset there ought to be version
        if version is not None:
            version_number += int(version["name"])

        hierarchy = asset['data']['parents']
        if hierarchy:
            # hierarchy = os.path.sep.join(hierarchy)
            hierarchy = os.path.join(*hierarchy)
        application = lib.get_application(os.environ["AVALON_APP_NAME"])
        template_data = {"root": api.Session["AVALON_PROJECTS"],
                         "project": {"name": project_name,
                                     "code": project['data']['code']},
                         "silo": silo,
                         "family": instance.data['family'],
                         "asset": asset_name,
                         "subset": subset_name,
                         "version": version_number,
                         "hierarchy": hierarchy,
                         "representation": "TEMP",
                         "app": application["application_dir"]}

        instance.data["template"] = template
        instance.data["assumedTemplateData"] = template_data

        # We take the parent folder of representation 'filepath'
        instance.data["assumedDestination"] = os.path.dirname(
            (anatomy.format(template_data)).publish.path
        )
