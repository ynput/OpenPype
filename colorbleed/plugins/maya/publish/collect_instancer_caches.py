import maya.cmds as cmds

import pyblish.api


class CollectInstancerCaches(pyblish.api.InstancePlugin):
    """For an Instancer collect the history.

    This would collect its particles with nucleus and cacheFile

    """

    order = pyblish.api.CollectorOrder + 0.495
    families = ['colorbleed.instancer']
    label = "Instancer Cache Files"

    def process(self, instance):

        members = instance.data.get("exactExportMembers", None)
        assert members, "Instancer must have members"

        resources = instance.data.get("resources", [])
        caches = cmds.ls(members, type="cacheFile")

        errors = False
        for cache in caches:

            self.log.debug("Collecting cache files for: {0}".format(cache))

            files = cmds.cacheFile(cache, query=True, fileName=True)

            # Ensure there are any files and the cacheFile is linked
            # correctly.
            if not files:
                errors = True
                self.log.error("Cache has no files: %s" % cache)
                continue

            source = files[0]  # The first file is the .xml file

            # TODO: Filter the files to only contain the required frame range.

            resource = {"tags": ["maya", "node", "cacheFile"],
                        "node": cache,
                        "source": source,
                        "files": files,
                        "subfolder": "caches"}

            resources.append(resource)

        # Store on the instance
        instance.data['resources'] = resources

        if errors:
            raise RuntimeError("Errors during collecting caches. "
                               "Are the caches linked correctly?")
