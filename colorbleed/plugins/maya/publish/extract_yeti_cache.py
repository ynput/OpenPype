import os
import json
import pprint

from maya import cmds

import colorbleed.api
from cb.utils.maya import context


class ExtractYetiProcedural(colorbleed.api.Extractor):
    """Produce an alembic of just point positions and normals.

    Positions and normals are preserved, but nothing more,
    for plain and predictable point caches.

    """

    label = "Extract Yeti"
    hosts = ["maya"]
    families = ["colorbleed.yetiRig"]

    def process(self, instance):

        yeti_nodes = cmds.ls(instance, type="pgYetiMaya")
        if not yeti_nodes:
            raise RuntimeError("No pgYetiMaya nodes found in the instance")

        # Define extract output file path
        dirname = self.staging_dir(instance)

        # Yeti related staging dirs
        data_file = os.path.join(dirname, "yeti_settings.json")
        maya_path = os.path.join(dirname, "yeti_rig.ma")

        self.log.info("Writing out cache")
        # Start writing the files for snap shot
        # <NAME> will be replace by the Yeti node name
        path = os.path.join(dirname, "cache_<NAME>.0001.fur")
        cmds.pgYetiCommand(yeti_nodes,
                           writeCache=path,
                           range=(1, 1),
                           sampleTimes="0.0 1.0",
                           updateViewport=False,
                           generatePreview=False)

        cache_files = [x for x in os.listdir(dirname) if x.endswith(".fur")]

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

            # Store assumed imageSearchPath
            settings["imageSearchPath"] = image_search_path

            with open(data_file, "w") as fp:
                json.dump(settings, fp, ensure_ascii=False)

        attr_value = {"%s.imageSearchPath" % n: image_search_path for
                      n in yeti_nodes}

        with context.attribute_value(attr_value):
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

        instance.data["files"].extend([cache_files,
                                       "yeti_rig.ma",
                                       "yeti_settings.json"])

        self.log.info("Extracted {} to {}".format(instance, dirname))

        cmds.select(clear=True)
