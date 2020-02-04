import os
import copy

import pyblish.api
from avalon import io


class IntegrateResourcesPath(pyblish.api.InstancePlugin):
    """Generate the assumed destination path where the file will be stored"""

    label = "Integrate Prepare Resource"
    order = pyblish.api.IntegratorOrder - 0.05
    families = ["clip",  "projectfile", "plate"]

    def process(self, instance):
        template_data = copy.deepcopy(instance.data["anatomyData"])

        anatomy = instance.context.data["anatomy"]
        frame_padding = int(anatomy.templates["render"]["padding"])

        # add possible representation specific key to anatomy data
        # TODO ability to set host specific "frame" value
        template_data.update({
            "frame": ("#" * frame_padding),
            "representation": "TEMP"
        })

        anatomy_filled = anatomy.format(template_data)

        template_names = ["publish"]
        for repre in instance.data["representations"]:
            template_name = repre.get("anatomy_template")
            if template_name and template_name not in template_names:
                template_names.append(template_name)

        resources = instance.data.get("resources", list())
        transfers = instance.data.get("transfers", list())

        for template_name in template_names:
            mock_template = anatomy_filled[template_name]["path"]

            # For now assume resources end up in a "resources" folder in the
            # published folder
            mock_destination = os.path.join(
                os.path.dirname(mock_template), "resources"
            )

            # Clean the path
            mock_destination = os.path.abspath(
                os.path.normpath(mock_destination)
            ).replace("\\", "/")

            # Define resource destination and transfers
            for resource in resources:
                # Add destination to the resource
                source_filename = os.path.basename(
                    resource["source"]).replace("\\", "/")
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
                    fdest = os.path.join(
                        mock_destination, fname).replace("\\", "/")
                    transfers.append([fsrc, fdest])

        instance.data["resources"] = resources
        instance.data["transfers"] = transfers
