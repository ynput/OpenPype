import pyblish.api
import ftrack


class IntegrateFtrack(pyblish.api.InstancePlugin):
    """ Creating components in Ftrack. """

    order = pyblish.api.IntegratorOrder + 0.4
    label = "Ftrack"

    def process(self, instance):

        # Skipping instance if ftrackData isn"t present.
        if not instance.context.has_data("ftrackData"):
            msg = "No ftrackData present. "
            msg += "Skipping this instance: \"%s\"" % instance
            self.log.info(msg)
            return

        # Skipping instance if ftrackComponents isn"t present.
        if not instance.has_data("ftrackComponents"):
            msg = "No ftrackComponents present. "
            msg += "Skipping this instance: \"%s\"" % instance
            self.log.info(msg)
            return

        asset_version = instance.data["ftrackAssetVersion"]
        version = ftrack.AssetVersion(asset_version["id"])

        # Get existing component names.
        existing_component_names = []
        for component in version.getComponents():
            existing_component_names.append(component.getName())

        components = instance.data("ftrackComponents")
        for component_name in instance.data("ftrackComponents"):

            # Get path to component.
            path = ""
            if "path" in components[component_name]:
                path = components[component_name]["path"]

            # If no path existing to the component, we skip to the next.
            if not path:
                continue

            # Assuming default picked location unless others specified.
            location = ftrack.pickLocation()
            if "location" in components[component_name]:
                location = components[component_name]["location"]

            # Get existing component.
            component = None
            if component_name in existing_component_names:
                component = version.getComponent(name=component_name)
                msg = "Found existing \"{0}\" component."
                self.log.info(msg.format(component_name))

            # To overwrite we have to delete the existing component and
            # create a new one. This is to ensure the data gets to the
            # location correctly.
            if "overwrite" in components[component_name] and component:
                msg = "Removing component in location: \"{0}\"."
                self.log.info(msg.format(location.getName()))
                location.removeComponent(component)

                msg = "Deleting \"{0}\" component."
                self.log.info(msg.format(component_name))
                component.delete()
                component = None

            if not component:
                msg = "Creating \"{0}\" component, with data path: \"{1}\"."
                self.log.info(msg.format(component_name, path))
                component = version.createComponent(name=component_name,
                                                    path=path,
                                                    location=location)

            cid = component.getId()
            instance.data["ftrackComponents"][component_name]["id"] = cid

            # make reviewable
            if "reviewable" in components[component_name]:
                upload = components[component_name]['reviewable']#True
                for component in version.getComponents():
                    if component_name in ("ftrackreview-mp4",
                                          "ftrackreview-webm"):
                        upload = False
                        break
                if upload:
                    ftrack.Review.makeReviewable(version, path)
