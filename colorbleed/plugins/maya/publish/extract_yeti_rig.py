import os

from maya import cmds

import colorbleed.api
from cb.utils.maya import context
reload(context)


class ExtractYetiRig(colorbleed.api.Extractor):
    """Produce an alembic of just point positions and normals.

    Positions and normals are preserved, but nothing more,
    for plain and predictable point caches.

    """

    label = "Extract Yeti Rig"
    hosts = ["maya"]
    families = ["colorbleed.yetiRig", "colorbleed.yeticache"]

    def process(self, instance):

        yeti_nodes = cmds.ls(instance, type="pgYetiMaya")
        if not yeti_nodes:
            raise RuntimeError("No pgYetiMaya nodes found in the instance")

        # Define extract output file path
        dirname = self.staging_dir(instance)

        # Yeti related staging dirs
        maya_path = os.path.join(dirname, "yeti_rig.ma")

        self.log.info("Writing metadata file")
        image_search_path = ""
        settings = instance.data.get("settings", None)
        if settings is not None:

            # Create assumed destination folder for imageSearchPath
            assumed_temp_data = instance.data["assumedTemplateData"]
            template = instance.data["template"]
            template_formatted = template.format(**assumed_temp_data)

            destination_folder = os.path.dirname(template_formatted)
            image_search_path = os.path.join(destination_folder, "resources")
            image_search_path = os.path.normpath(image_search_path)

        attr_value = {"%s.imageSearchPath" % n: image_search_path for
                      n in yeti_nodes}

        with context.attribute_values(attr_value):
            cmds.select(instance.data["setMembers"], noExpand=True)
            cmds.file(maya_path,
                      force=True,
                      exportSelected=True,
                      typ="mayaAscii",
                      preserveReferences=False,
                      constructionHistory=False,
                      shader=False)

        # Ensure files can be stored
        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"].extend(["yeti_rig.ma",
                                       "yeti_settings.json"])

        self.log.info("Extracted {} to {}".format(instance, dirname))

        cmds.select(clear=True)
