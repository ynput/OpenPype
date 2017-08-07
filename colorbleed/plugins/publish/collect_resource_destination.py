import pyblish.api
import os

import avalon.io as io


class CollectResourceDestination(pyblish.api.InstancePlugin):
    """This plug-ins displays the comment dialog box per default"""

    label = "Collect Resource Destination"
    order = pyblish.api.CollectorOrder + 0.499

    def process(self, instance):

        self.create_destination_template(instance)

        template_data = instance.data["assumedTemplateData"]
        template = instance.data["template"]

        mock_template = template.format(**template_data)

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

        # get all the stuff from the database
        subset_name = instance.data["subset"]
        project_name = os.environ["AVALON_PROJECT"]

        project = io.find_one({"type": "project",
                               "name": project_name},
                              projection={"config": True})
        template = project["config"]["template"]["publish"]

        subset = io.find_one({"type": "subset",
                              "name": subset_name})

        # assume there is no version yet, we start at `1`
        version_number = 1
        if subset is not None:
            version = io.find_one({"type": "version",
                                   "parent": subset["_id"]},
                                  sort=[("name", -1)])
            # if there is a subset there ought to be version
            version_number += version["name"]

        template_data = {"root": os.environ["AVALON_ROOT"],
                         "project": project_name,
                         "silo": os.environ["AVALON_SILO"],
                         "asset": instance.data["asset"],
                         "subset": subset_name,
                         "version": version_number,
                         "representation": "TEMP"}

        instance.data["assumedTemplateData"] = template_data
        instance.data["template"] = template
