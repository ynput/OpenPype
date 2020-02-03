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
        project_entity = instance.context["projectEntity"]
        asset_entity = instance.context["assetEntity"]

        template_data = copy.deepcopy(instance.data["anatomyData"])

        asset_name = instance.data["asset"]
        if asset_name != asset_entity["name"]:
            asset_entity = io.find_one({
                "type": "asset",
                "name": asset_name,
                "parent": project_entity["_id"]
            })
            assert asset_entity, (
                "No asset found by the name '{}' in project '{}'".format(
                    asset_name, project_entity["name"]
                )
            )

            instance.data["assetEntity"] = asset_entity

            template_data["name"] = asset_entity["name"]
            silo_name = asset_entity.get("silo")
            if silo_name:
                template_data["silo"] = silo_name

            parents = asset_entity["data"].get("parents") or []
            hierarchy = "/".join(parents)
            template_data["hierarchy"] = hierarchy

        subset_name = instance.data["subset"]
        self.log.info(subset_name)

        subset = io.find_one({
            "type": "subset",
            "name": subset_name,
            "parent": asset_entity["_id"]
        })

        # assume there is no version yet, we start at `1`
        version = None
        version_number = 1
        if subset is not None:
            version = io.find_one(
                {
                    "type": "version",
                    "parent": subset["_id"]
                },
                sort=[("name", -1)]
            )

        # if there is a subset there ought to be version
        if version is not None:
            version_number += version["name"]

        if instance.data.get('version'):
            version_number = int(instance.data.get('version'))

        anatomy = instance.context.data["anatomy"]
        padding = int(anatomy.templates['render']['padding'])

        template_data.update({
            "subset": subset_name,
            "frame": ('#' * padding),
            "version": version_number,
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
