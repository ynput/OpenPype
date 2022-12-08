import os

from maya import cmds
import arnold

from openpype.pipeline import publish
from openpype.hosts.maya.api.lib import maintained_selection, attribute_values


class ExtractAssStandin(publish.Extractor):
    """Extract the content of the instance to a ass file"""

    label = "Arnold Scene Source (.ass)"
    hosts = ["maya"]
    families = ["ass"]
    asciiAss = False

    def process(self, instance):

        sequence = instance.data.get("exportSequence", False)

        staging_dir = self.staging_dir(instance)
        filename = "{}.ass".format(instance.name)
        filenames = []
        file_path = os.path.join(staging_dir, filename)

        # Mask
        mask = arnold.AI_NODE_ALL

        node_types = {
            "options": arnold.AI_NODE_OPTIONS,
            "camera": arnold.AI_NODE_CAMERA,
            "light": arnold.AI_NODE_LIGHT,
            "shape": arnold.AI_NODE_SHAPE,
            "shader": arnold.AI_NODE_SHADER,
            "override": arnold.AI_NODE_OVERRIDE,
            "driver": arnold.AI_NODE_DRIVER,
            "filter": arnold.AI_NODE_FILTER,
            "color_manager": arnold.AI_NODE_COLOR_MANAGER,
            "operator": arnold.AI_NODE_OPERATOR
        }

        for key in node_types.keys():
            if instance.data.get("mask" + key.title()):
                mask = mask ^ node_types[key]

        # Motion blur
        values = {
            "defaultArnoldRenderOptions.motion_blur_enable": instance.data.get(
                "motionBlur", True
            ),
            "defaultArnoldRenderOptions.motion_steps": instance.data.get(
                "motionBlurKeys", 2
            ),
            "defaultArnoldRenderOptions.motion_frames": instance.data.get(
                "motionBlurLength", 0.5
            )
        }

        # Write out .ass file
        kwargs = {
            "filename": file_path,
            "selected": True,
            "asciiAss": self.asciiAss,
            "shadowLinks": True,
            "lightLinks": True,
            "boundingBox": True,
            "expandProcedurals": instance.data.get("expandProcedurals", False),
            "camera": instance.data["camera"],
            "mask": mask
        }

        self.log.info("Writing: '%s'" % file_path)
        with attribute_values(values):
            with maintained_selection():
                self.log.info(
                    "Writing: {}".format(instance.data["setMembers"])
                )
                cmds.select(instance.data["setMembers"], noExpand=True)

                self.log.info("Extracting ass sequence")

                # Collect the start and end including handles
                kwargs.update({
                    "start": instance.data.get("frameStartHandle", 1),
                    "end": instance.data.get("frameEndHandle", 1),
                    "step": instance.data.get("step", 0)
                })

                exported_files = cmds.arnoldExportAss(**kwargs)

                for file in exported_files:
                    filenames.append(os.path.split(file)[1])

                self.log.info("Exported: {}".format(filenames))

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'ass',
            'ext': 'ass',
            'files': filenames if len(filenames) > 1 else filenames[0],
            "stagingDir": staging_dir,
            'frameStart': kwargs["start"]
        }

        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s"
                      % (instance.name, staging_dir))
