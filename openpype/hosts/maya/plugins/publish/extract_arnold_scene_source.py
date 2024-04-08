import os
from collections import defaultdict
import json

from maya import cmds
import arnold

from openpype.pipeline import publish
from openpype.hosts.maya.api import lib


class ExtractArnoldSceneSource(publish.Extractor):
    """Extract the content of the instance to an Arnold Scene Source file."""

    label = "Extract Arnold Scene Source"
    hosts = ["maya"]
    families = ["ass"]
    asciiAss = True

    def _pre_process(self, instance, staging_dir):
        file_path = os.path.join(staging_dir, "{}.ass".format(instance.name))

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

        if "representations" not in instance.data:
            instance.data["representations"] = []

        return attribute_data, kwargs

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        attribute_data, kwargs = self._pre_process(instance, staging_dir)

        filenames = self._extract(
            instance.data["members"], attribute_data, kwargs
        )

        self._post_process(
            instance, filenames, staging_dir, kwargs["startFrame"]
        )

    def _post_process(self, instance, filenames, staging_dir, frame_start):
        nodes_by_id = self._nodes_by_id(instance[:])
        representation = {
            "name": "ass",
            "ext": "ass",
            "files": filenames if len(filenames) > 1 else filenames[0],
            "stagingDir": staging_dir,
            "frameStart": frame_start
        }

        instance.data["representations"].append(representation)

        json_path = os.path.join(
            staging_dir, "{}.json".format(instance.name)
        )
        with open(json_path, "w") as f:
            json.dump(nodes_by_id, f)

        representation = {
            "name": "json",
            "ext": "json",
            "files": os.path.basename(json_path),
            "stagingDir": staging_dir
        }

        instance.data["representations"].append(representation)

        self.log.debug(
            "Extracted instance {} to: {}".format(instance.name, staging_dir)
        )

    def _nodes_by_id(self, nodes):
        nodes_by_id = defaultdict(list)

        for node in nodes:
            id = lib.get_id(node)

            if id is None:
                continue

            # Converting Maya hierarchy separator "|" to Arnold separator "/".
            nodes_by_id[id].append(node.replace("|", "/"))

        return nodes_by_id

    def _extract(self, nodes, attribute_data, kwargs):
        filenames = []
        with lib.attribute_values(attribute_data):
            with lib.maintained_selection():
                self.log.debug(
                    "Writing: {}".format(nodes)
                )
                cmds.select(nodes, noExpand=True)

                self.log.debug(
                    "Extracting ass sequence with: {}".format(kwargs)
                )

                exported_files = cmds.arnoldExportAss(**kwargs)

                for file in exported_files:
                    filenames.append(os.path.split(file)[1])

                self.log.debug("Exported: {}".format(filenames))

        return filenames


class ExtractArnoldSceneSourceProxy(ExtractArnoldSceneSource):
    """Extract the content of the instance to an Arnold Scene Source file."""

    label = "Extract Arnold Scene Source Proxy"
    hosts = ["maya"]
    families = ["assProxy"]
    asciiAss = True

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        attribute_data, kwargs = self._pre_process(instance, staging_dir)

        filenames, _ = self._duplicate_extract(
            instance.data["members"], attribute_data, kwargs
        )

        self._post_process(
            instance, filenames, staging_dir, kwargs["startFrame"]
        )

        kwargs["filename"] = os.path.join(
            staging_dir, "{}_proxy.ass".format(instance.name)
        )

        filenames, _ = self._duplicate_extract(
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

    def _duplicate_extract(self, nodes, attribute_data, kwargs):
        self.log.debug(
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
                    node, shapes=True, noIntermediate=True
                )
                if not shapes:
                    continue

                basename = cmds.duplicate(node)[0]
                parents = cmds.ls(node, long=True)[0].split("|")[:-1]
                duplicate_transform = "|".join(parents + [basename])

                if cmds.listRelatives(duplicate_transform, parent=True):
                    duplicate_transform = cmds.parent(
                        duplicate_transform, world=True
                    )[0]

                basename = node.rsplit("|", 1)[-1].rsplit(":", 1)[-1]
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

            nodes_by_id = self._nodes_by_id(duplicate_nodes)
            filenames = self._extract(duplicate_nodes, attribute_data, kwargs)

        return filenames, nodes_by_id
