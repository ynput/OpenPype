import os
from pprint import pformat
import nuke
import pyblish.api
import openpype.api
from openpype.hosts.nuke.api.lib import (
    maintained_selection,
    select_nodes
)


class ExtractModel(openpype.api.Extractor):
    """ 3D model exctractor
    """
    label = 'Exctract Model'
    order = pyblish.api.ExtractorOrder
    families = ["model"]
    hosts = ["nuke"]

    # presets
    write_geo_knobs = [
        ("file_type", "abc"),
        ("storageFormat", "Ogawa"),
        ("writeGeometries", True),
        ("writePointClouds", False),
        ("writeAxes", False)
    ]

    def process(self, instance):
        handle_start = instance.context.data["handleStart"]
        handle_end = instance.context.data["handleEnd"]
        first_frame = int(nuke.root()["first_frame"].getValue())
        last_frame = int(nuke.root()["last_frame"].getValue())

        self.log.info("instance.data: `{}`".format(
            pformat(instance.data)))

        rm_nodes = list()
        model_node = instance[0]
        self.log.info("Crating additional nodes")
        subset = instance.data["subset"]
        staging_dir = self.staging_dir(instance)

        extension = next((k[1] for k in self.write_geo_knobs
                          if k[0] == "file_type"), None)
        if not extension:
            raise RuntimeError(
                "Bad config for extension in presets. "
                "Talk to your supervisor or pipeline admin")

        # create file name and path
        filename = subset + ".{}".format(extension)
        file_path = os.path.join(staging_dir, filename).replace("\\", "/")

        with maintained_selection():
            # select model node
            select_nodes([model_node])

            # create write geo node
            wg_n = nuke.createNode("WriteGeo")
            wg_n["file"].setValue(file_path)
            # add path to write to
            for k, v in self.write_geo_knobs:
                wg_n[k].setValue(v)
            rm_nodes.append(wg_n)

            # write out model
            nuke.execute(
                wg_n,
                int(first_frame),
                int(last_frame)
            )
            # erase additional nodes
            for n in rm_nodes:
                nuke.delete(n)

            self.log.info(file_path)

        # create representation data
        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': extension,
            'ext': extension,
            'files': filename,
            "stagingDir": staging_dir,
            "frameStart": first_frame,
            "frameEnd": last_frame
        }
        instance.data["representations"].append(representation)

        instance.data.update({
            "path": file_path,
            "outputDir": staging_dir,
            "ext": extension,
            "handleStart": handle_start,
            "handleEnd": handle_end,
            "frameStart": first_frame + handle_start,
            "frameEnd": last_frame - handle_end,
            "frameStartHandle": first_frame,
            "frameEndHandle": last_frame,
        })

        self.log.info("Extracted instance '{0}' to: {1}".format(
            instance.name, file_path))
