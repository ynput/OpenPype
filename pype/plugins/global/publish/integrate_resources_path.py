import os
import pyblish.api


class IntegrateResourcesPath(pyblish.api.InstancePlugin):
    """Generate directory path where the files and resources will be stored"""

    label = "Integrate Resources Path"
    order = pyblish.api.IntegratorOrder - 0.05
    families = ["clip",  "projectfile", "plate"]

    def process(self, instance):
        resources = instance.data.get("resources") or []
        transfers = instance.data.get("transfers") or []

        if not resources and not transfers:
            self.log.debug(
                "Instance does not have `resources` and `transfers`"
            )
            return

        resources_folder = instance.data["resourcesDir"]

        # Define resource destination and transfers
        for resource in resources:
            # Add destination to the resource
            source_filename = os.path.basename(
                resource["source"]).replace("\\", "/")
            destination = os.path.join(resources_folder, source_filename)

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
                    resources_folder, fname
                ).replace("\\", "/")
                transfers.append([fsrc, fdest])

        instance.data["resources"] = resources
        instance.data["transfers"] = transfers
