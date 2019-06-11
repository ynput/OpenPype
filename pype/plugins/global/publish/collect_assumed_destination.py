import os
import pyblish.api

from avalon import io, api


class CollectAssumedDestination(pyblish.api.ContextPlugin):
    """Generate the assumed destination path where the file will be stored"""

    label = "Collect Assumed Destination"
    order = pyblish.api.CollectorOrder + 0.498
    exclude_families = ["plate"]

    def process(self, context):

        for instance in context:
            if [ef for ef in self.exclude_families
                    if ef in instance.data["family"]]:
                self.log.info("Ignoring instance: {}".format(instance))
                return
            self.process_item(instance)

    def process_item(self, instance):

        self.create_destination_template(instance)

        template_data = instance.data["assumedTemplateData"]

        anatomy = instance.context.data['anatomy']
        # self.log.info(anatomy.anatomy())
        self.log.info(anatomy.templates)
        # template = anatomy.publish.path
        anatomy_filled = anatomy.format(template_data)
        self.log.info(anatomy_filled)
        mock_template = anatomy_filled["publish"]["path"]

        # For now assume resources end up in a "resources" folder in the
        # published folder
        mock_destination = os.path.join(os.path.dirname(mock_template),
                                        "resources")

        # Clean the path
        mock_destination = os.path.abspath(os.path.normpath(mock_destination))

        # Define resource destination and transfers
        resources = instance.data.get("resources", list())
        transfers = instance.data.get("transfers", list())
        for resource in resources:

            # Add destination to the resource
            source_filename = os.path.basename(resource["source"])
            destination = os.path.join(mock_destination, source_filename)

            # Force forward slashes to fix issue with software unable
            # to work correctly with backslashes in specific scenarios
            # (e.g. escape characters in PLN-151 V-Ray UDIM)
            destination = destination.replace("\\", "/")

            resource['destination'] = destination

            # Collect transfers for the individual files of the resource
            # e.g. all individual files of a cache or UDIM textures.
            files = resource['files']
            for fsrc in files:
                fname = os.path.basename(fsrc)
                fdest = os.path.join(mock_destination, fname)
                transfers.append([fsrc, fdest])

        instance.data["resources"] = resources
        instance.data["transfers"] = transfers

    def create_destination_template(self, instance):
        """Create a filepath based on the current data available

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

        # FIXME: io is not initialized at this point for shell host
        io.install()
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

        template_data = {"root": api.Session["AVALON_PROJECTS"],
                         "project": {"name": project_name,
                                     "code": project['data']['code']},
                         "silo": silo,
                         "family": instance.data['family'],
                         "asset": asset_name,
                         "subset": subset_name,
                         "version": version_number,
                         "hierarchy": hierarchy,
                         "representation": "TEMP"}

        instance.data["template"] = template
        instance.data["assumedTemplateData"] = template_data

        # We take the parent folder of representation 'filepath'
        instance.data["assumedDestination"] = os.path.dirname(
            (anatomy.format(template_data))["publish"]["path"]
        )
