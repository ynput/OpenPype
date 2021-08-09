import os
import pyblish.api


class ExtractWorkfileUrl(pyblish.api.ContextPlugin):
    """
        Modifies 'workfile' field to contain link to published workfile.

        Expects that batch contains only single workfile and matching
        (multiple) textures.
    """

    label = "Extract Workfile Url SP"
    hosts = ["standalonepublisher"]
    order = pyblish.api.ExtractorOrder

    families = ["textures"]

    def process(self, context):
        filepath = None

        # first loop for workfile
        for instance in context:
            if instance.data["family"] == 'workfile':
                anatomy = context.data['anatomy']
                template_data = instance.data.get("anatomyData")
                rep_name = instance.data.get("representations")[0].get("name")
                template_data["representation"] = rep_name
                template_data["ext"] = rep_name
                anatomy_filled = anatomy.format(template_data)
                template_filled = anatomy_filled["publish"]["path"]
                filepath = os.path.normpath(template_filled)
                self.log.info("Using published scene for render {}".format(
                    filepath))

        if not filepath:
            self.log.info("Texture batch doesn't contain workfile.")
            return

        # then apply to all textures
        for instance in context:
            if instance.data["family"] == 'textures':
                instance.data["versionData"]["workfile"] = filepath
