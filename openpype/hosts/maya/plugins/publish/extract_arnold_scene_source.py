import os

from maya import cmds
import arnold

from openpype.pipeline import publish
from openpype.hosts.maya.api import lib


class ExtractArnoldSceneSource(publish.Extractor):
    """Extract the content of the instance to an Arnold Scene Source file."""

    label = "Extract Arnold Scene Source"
    hosts = ["maya"]
    families = ["ass"]
    asciiAss = False

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        filename = "{}.ass".format(instance.name)
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
        attribute_data = {
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
            "startFrame": instance.data.get("frameStartHandle", 1),
            "endFrame": instance.data.get("frameEndHandle", 1),
            "frameStep": instance.data.get("step", 1),
            "selected": True,
            "asciiAss": self.asciiAss,
            "shadowLinks": True,
            "lightLinks": True,
            "boundingBox": True,
            "expandProcedurals": instance.data.get("expandProcedurals", False),
            "camera": instance.data["camera"],
            "mask": mask
        }

        filenames = self._extract(
            instance.data["contentMembers"], attribute_data, kwargs
        )

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": "ass",
            "ext": "ass",
            "files": filenames if len(filenames) > 1 else filenames[0],
            "stagingDir": staging_dir,
            "frameStart": kwargs["startFrame"]
        }

        instance.data["representations"].append(representation)

        self.log.info(
            "Extracted instance {} to: {}".format(instance.name, staging_dir)
        )

        # Extract proxy.
        if not instance.data.get("proxy", []):
            return

        kwargs["filename"] = file_path.replace(".ass", "_proxy.ass")
        filenames = self._extract(
            instance.data["proxy"], attribute_data, kwargs
        )

        representation = {
            "name": "proxy",
            "ext": "ass",
            "files": filenames if len(filenames) > 1 else filenames[0],
            "stagingDir": staging_dir,
            "frameStart": kwargs["startFrame"],
            "outputName": "proxy"
        }

        instance.data["representations"].append(representation)

    def _extract(self, nodes, attribute_data, kwargs):
        self.log.info(
            "Writing {} with:\n{}".format(kwargs["filename"], kwargs)
        )
        filenames = []
        # Duplicating nodes so they are direct children of the world. This
        # makes the hierarchy of any exported ass file the same.
        with lib.delete_after() as delete_bin:
            duplicate_nodes = []
            for node in nodes:
                # Only interested in transforms:
                if cmds.nodeType(node) != "transform":
                    continue

                # Only interested in transforms with shapes.
                shapes = cmds.listRelatives(
                    node, shapes=True, fullPath=True
                ) or []
                if not shapes:
                    continue

                parent = cmds.listRelatives(
                    node, parent=True, fullPath=True
                )[0]
                duplicate_transform = cmds.duplicate(node)[0]
                duplicate_transform = "{}|{}".format(
                    parent, duplicate_transform
                )


                if cmds.listRelatives(duplicate_transform, parent=True):
                    duplicate_transform = cmds.parent(
                        duplicate_transform, world=True
                    )[0]

                basename = node.split("|")[-1].split(":")[-1]
                duplicate_transform = cmds.rename(
                    duplicate_transform, basename
                )

                # Discard children nodes that are not shapes
                shapes = cmds.listRelatives(
                    duplicate_transform, shapes=True, fullPath=True
                )
                children = cmds.listRelatives(
                    duplicate_transform, children=True, fullPath=True
                )
                cmds.delete(set(children) - set(shapes))

                duplicate_nodes.append(duplicate_transform)
                duplicate_nodes.extend(shapes)
                delete_bin.append(duplicate_transform)

            # Copy cbId to mtoa_constant.
            for node in duplicate_nodes:
                lib.set_attribute("mtoa_constant_cbId", lib.get_id(node), node)

            with lib.attribute_values(attribute_data):
                with lib.maintained_selection():
                    self.log.info(
                        "Writing: {}".format(duplicate_nodes)
                    )
                    cmds.select(duplicate_nodes, noExpand=True)

                    self.log.info(
                        "Extracting ass sequence with: {}".format(kwargs)
                    )

                    exported_files = cmds.arnoldExportAss(**kwargs)

                    for file in exported_files:
                        filenames.append(os.path.split(file)[1])

                    self.log.info("Exported: {}".format(filenames))

        return filenames
