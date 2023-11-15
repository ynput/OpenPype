import os

from maya import cmds, mel
import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.maya.api import lib
from openpype.hosts.maya.api.gltf import extract_gltf


class ExtractGLB(publish.Extractor):

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract GLB"
    families = ["gltf"]

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        filename = "{0}.glb".format(instance.name)
        path = os.path.join(staging_dir, filename)

        cmds.loadPlugin("maya2glTF", quiet=True)

        nodes = instance[:]

        start_frame = instance.data('frameStart') or \
                      int(cmds.playbackOptions(query=True,
                                               animationStartTime=True))# noqa
        end_frame = instance.data('frameEnd') or \
                    int(cmds.playbackOptions(query=True,
                                             animationEndTime=True)) # noqa
        fps = mel.eval('currentTimeUnitToFPS()')

        options = {
            "sno": True,    # selectedNodeOnly
            "nbu": True,    # .bin instead of .bin0
            "ast": start_frame,
            "aet": end_frame,
            "afr": fps,
            "dsa": 1,
            "acn": instance.name,
            "glb": True,
            "vno": True    # visibleNodeOnly
        }

        self.log.debug("Extracting GLB to: {}".format(path))
        with lib.maintained_selection():
            cmds.select(nodes, hi=True, noExpand=True)
            extract_gltf(staging_dir,
                         instance.name,
                         **options)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'glb',
            'ext': 'glb',
            'files': filename,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)

        self.log.debug("Extract GLB successful to: {0}".format(path))
