# -*- coding: utf-8 -*-
"""Extract camera as Maya Scene."""
import os
import itertools

from maya import cmds

import openpype.api
from openpype.hosts.maya.api import lib


def massage_ma_file(path):
    """Clean up .ma file for backwards compatibility.

    Massage the .ma of baked camera to stay
    backwards compatible with older versions
    of Fusion (6.4)

    """
    # Get open file's lines
    f = open(path, "r+")
    lines = f.readlines()
    f.seek(0)  # reset to start of file

    # Rewrite the file
    for line in lines:
        # Skip all 'rename -uid' lines
        stripped = line.strip()
        if stripped.startswith("rename -uid "):
            continue

        f.write(line)

    f.truncate()  # remove remainder
    f.close()


def grouper(iterable, n, fillvalue=None):
    """Collect data into fixed-length chunks or blocks.

    Examples:
        grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx

    """
    args = [iter(iterable)] * n
    from six.moves import zip_longest
    return zip_longest(fillvalue=fillvalue, *args)


def unlock(plug):
    """Unlocks attribute and disconnects inputs for a plug.

    This will also recursively unlock the attribute
    upwards to any parent attributes for compound
    attributes, to ensure it's fully unlocked and free
    to change the value.

    """
    node, attr = plug.rsplit(".", 1)

    # Unlock attribute
    cmds.setAttr(plug, lock=False)

    # Also unlock any parent attribute (if compound)
    parents = cmds.attributeQuery(attr, node=node, listParent=True)
    if parents:
        for parent in parents:
            unlock("{0}.{1}".format(node, parent))

    # Break incoming connections
    connections = cmds.listConnections(plug,
                                       source=True,
                                       destination=False,
                                       plugs=True,
                                       connections=True)
    if connections:
        for destination, source in grouper(connections, 2):
            cmds.disconnectAttr(source, destination)


class ExtractCameraMayaScene(openpype.api.Extractor):
    """Extract a Camera as Maya Scene.

    This will create a duplicate of the camera that will be baked *with*
    substeps and handles for the required frames. This temporary duplicate
    will be published.

    The cameras gets baked to world space by default. Only when the instance's
    `bakeToWorldSpace` is set to False it will include its full hierarchy.

    Note:
        The extracted Maya ascii file gets "massaged" removing the uuid values
        so they are valid for older versions of Fusion (e.g. 6.4)

    """

    label = "Camera (Maya Scene)"
    hosts = ["maya"]
    families = ["camera"]
    scene_type = "ma"

    def process(self, instance):
        """Plugin entry point."""
        # get settings
        ext_mapping = (
            instance.context.data["project_settings"]["maya"]["ext_mapping"]
        )
        if ext_mapping:
            self.log.info("Looking in settings for scene type ...")
            # use extension mapping for first family found
            for family in self.families:
                try:
                    self.scene_type = ext_mapping[family]
                    self.log.info(
                        "Using {} as scene type".format(self.scene_type))
                    break
                except KeyError:
                    # no preset found
                    pass

        # Collect the start and end including handles
        start = instance.data["frameStartHandle"]
        end = instance.data["frameEndHandle"]

        step = instance.data.get("step", 1.0)
        bake_to_worldspace = instance.data("bakeToWorldSpace", True)

        if not bake_to_worldspace:
            self.log.warning("Camera (Maya Scene) export only supports world"
                             "space baked camera extractions. The disabled "
                             "bake to world space is ignored...")

        # get cameras
        members = instance.data['setMembers']
        cameras = cmds.ls(members, leaf=True, shapes=True, long=True,
                          dag=True, type="camera")

        # validate required settings
        assert len(cameras) == 1, "Single camera must be found in extraction"
        assert isinstance(step, float), "Step must be a float value"
        camera = cameras[0]
        transform = cmds.listRelatives(camera, parent=True, fullPath=True)

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        filename = "{0}.{1}".format(instance.name, self.scene_type)
        path = os.path.join(dir_path, filename)

        # Perform extraction
        with lib.maintained_selection():
            with lib.evaluation("off"):
                with lib.suspended_refresh():
                    if bake_to_worldspace:
                        self.log.info(
                            "Performing camera bakes: {}".format(transform))
                        baked = lib.bake_to_world_space(
                            transform,
                            frame_range=[start, end],
                            step=step
                        )
                        baked_shapes = cmds.ls(baked,
                                               type="camera",
                                               dag=True,
                                               shapes=True,
                                               long=True)
                    else:
                        baked_shapes = cameras
                    # Fix PLN-178: Don't allow background color to be non-black
                    for cam in baked_shapes:
                        attrs = {"backgroundColorR": 0.0,
                                 "backgroundColorG": 0.0,
                                 "backgroundColorB": 0.0,
                                 "overscan": 1.0}
                        for attr, value in attrs.items():
                            plug = "{0}.{1}".format(cam, attr)
                            unlock(plug)
                            cmds.setAttr(plug, value)

                    self.log.info("Performing extraction..")
                    cmds.select(baked_shapes, noExpand=True)
                    cmds.file(path,
                              force=True,
                              typ="mayaAscii" if self.scene_type == "ma" else "mayaBinary",  # noqa: E501
                              exportSelected=True,
                              preserveReferences=False,
                              constructionHistory=False,
                              channels=True,  # allow animation
                              constraints=False,
                              shader=False,
                              expressions=False)

                    # Delete the baked hierarchy
                    if bake_to_worldspace:
                        cmds.delete(baked)
                    if self.scene_type == "ma":
                        massage_ma_file(path)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': self.scene_type,
            'ext': self.scene_type,
            'files': filename,
            "stagingDir": dir_path,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '{0}' to: {1}".format(
            instance.name, path))
