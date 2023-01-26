import os
import pyblish.api
from openpype.pipeline import publish
from pymxs import runtime as rt
from openpype.hosts.max.api import (
    maintained_selection,
    get_all_children
)


class ExtractMaxSceneRaw(publish.Extractor):
    """
    Extract Raw Max Scene with SaveSelected
    """

    order = pyblish.api.ExtractorOrder - 0.2
    label = "Max Scene(Raw)"
    hosts = ["max"]
    families = ["camera"]

    def process(self, instance):
        container = instance.data["instance_node"]

        # publish the raw scene for camera
        self.log.info("Extracting Camera ...")

        stagingdir = self.staging_dir(instance)
        filename = "{name}.max".format(**instance.data)

        max_path = os.path.join(stagingdir, filename)
        self.log.info("Writing max file '%s' to '%s'" % (filename,
                                                         max_path))

        if "representations" not in instance.data:
            instance.data["representations"] = []

        #add extra blacklash for saveNodes in MaxScript
        re_max_path = stagingdir + "\\\\" + filename
        # saving max scene
        raw_export_cmd = (
            f"""
sel = getCurrentSelection()
for s in sel do
(
 	select s
 	f="{re_max_path}"
 	print f
 	saveNodes selection f quiet:true
)
            """)

        self.log.debug(f"Executing Maxscript command: {raw_export_cmd}")

        with maintained_selection():
            # need to figure out how to select the camera
            rt.select(get_all_children(rt.getNodeByName(container)))
            rt.execute(raw_export_cmd)

        self.log.info("Performing Extraction ...")
        representation = {
            'name': 'max',
            'ext': 'max',
            'files': filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)
        self.log.info("Extracted instance '%s' to: %s" % (instance.name,
                                                          max_path))