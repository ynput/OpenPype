import os
import contextlib

from maya import cmds
import arnold

from openpype.pipeline import publish
from openpype.hosts.maya.api.lib import maintained_selection


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
        filenames = list()
        file_path = os.path.join(staging_dir, filename)

        kwargs = {
            "filename": file_path,
            "selected": True,
            "asciiAss": self.asciiAss,
            "shadowLinks": True,
            "lightLinks": True,
            "boundingBox": True,
            "expandProcedurals": instance.data.get("expandProcedurals", False),
            "camera": instance.data["camera"],
            "mask": self.get_ass_export_mask(instance)
        }

        # Motion blur
        motion_blur = instance.data.get("motionBlur", True)
        motion_blur_keys = instance.data.get("motionBlurKeys", 2)
        motion_blur_length = instance.data.get("motionBlurLength", 0.5)

        # Write out .ass file
        self.log.info("Writing: '%s'" % file_path)
        with self.motion_blur_ctx(motion_blur, motion_blur_keys, motion_blur_length):
            with maintained_selection():
                self.log.info(
                    "Writing: {}".format(instance.data["setMembers"])
                )
                cmds.select(instance.data["setMembers"], noExpand=True)

                if sequence:
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
                else:
                    self.log.info("Extracting ass")
                    cmds.arnoldExportAss(**kwargs)
                    self.log.info("Extracted {}".format(filename))
                    filenames = filename
                    optionals = [
                        "frameStart", "frameEnd", "step", "handles",
                        "handleEnd", "handleStart"
                    ]
                    for key in optionals:
                        instance.data.pop(key, None)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'ass',
            'ext': 'ass',
            'files': filenames,
            "stagingDir": staging_dir
        }

        if sequence:
            representation['frameStart'] = kwargs["start"]

        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s"
                      % (instance.name, staging_dir))

    #This should be separated out as library function that takes some
    #attributes to modify with values. The function then resets to original
    #values.
    @contextlib.contextmanager
    def motion_blur_ctx(self, force, keys, length):
        if not force:
            yield
            return

        cmb = cmds.getAttr("defaultArnoldRenderOptions.motion_blur_enable")
        ckeys = cmds.getAttr("defaultArnoldRenderOptions.motion_steps")
        clen = cmds.getAttr("defaultArnoldRenderOptions.motion_frames")

        cmds.setAttr("defaultArnoldRenderOptions.motion_blur_enable", 1)
        if keys > 0:
            cmds.setAttr("defaultArnoldRenderOptions.motion_steps", keys)
        if length >= 0:
            cmds.setAttr("defaultArnoldRenderOptions.motion_frames", length)

        try:
            yield
        finally:
            cmds.setAttr("defaultArnoldRenderOptions.motion_blur_enable", cmb)
            cmds.setAttr("defaultArnoldRenderOptions.motion_steps", ckeys)
            cmds.setAttr("defaultArnoldRenderOptions.motion_frames", clen)

    #This should be refactored to lib. probably just need the node_types directionary
    def get_ass_export_mask(self, instance):
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

        return mask
