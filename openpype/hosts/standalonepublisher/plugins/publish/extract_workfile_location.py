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
                template_obj = anatomy.templates_obj["publish"]["path"]
                template_filled = template_obj.format_strict(template_data)
                filepath = os.path.normpath(template_filled)
                self.log.info("Using published scene for render {}".format(
                    filepath))
                break

        if not filepath:
            self.log.info("Texture batch doesn't contain workfile.")
            return

        # then apply to all textures
        for instance in context:
            if instance.data["family"] == 'textures':
                instance.data["versionData"]["workfile"] = filepath
