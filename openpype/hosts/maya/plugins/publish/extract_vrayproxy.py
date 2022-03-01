import os

from maya import cmds

import openpype.api
from openpype.hosts.maya.api.lib import maintained_selection


class ExtractVRayProxy(openpype.api.Extractor):
    """Extract the content of the instance to a vrmesh file

    Things to pay attention to:
        - If animation is toggled, are the frames correct
        -
    """

    label = "VRay Proxy (.vrmesh)"
    hosts = ["maya"]
    families = ["vrayproxy"]

    def process(self, instance):

        staging_dir = self.staging_dir(instance)
        file_name = "{}.vrmesh".format(instance.name)
        file_path = os.path.join(staging_dir, file_name)

        anim_on = instance.data["animation"]
        if not anim_on:
            # Remove animation information because it is not required for
            # non-animated subsets
            keys = ["frameStart", "frameEnd",
                    "handleStart", "handleEnd",
                    "frameStartHandle", "frameEndHandle",
                    # Backwards compatibility
                    "handles"]
            for key in keys:
                instance.data.pop(key, None)

            start_frame = 1
            end_frame = 1
        else:
            start_frame = instance.data["frameStartHandle"]
            end_frame = instance.data["frameEndHandle"]

        vertex_colors = instance.data.get("vertexColors", False)

        # Write out vrmesh file
        self.log.info("Writing: '%s'" % file_path)
        with maintained_selection():
            cmds.select(instance.data["setMembers"], noExpand=True)
            cmds.vrayCreateProxy(exportType=1,
                                 dir=staging_dir,
                                 fname=file_name,
                                 animOn=anim_on,
                                 animType=3,
                                 startFrame=start_frame,
                                 endFrame=end_frame,
                                 vertexColorsOn=vertex_colors,
                                 ignoreHiddenObjects=True,
                                 createProxyNode=False)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'vrmesh',
            'ext': 'vrmesh',
            'files': file_name,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s"
                      % (instance.name, staging_dir))
