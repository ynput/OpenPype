# -*- coding: utf-8 -*-
"""Extract camera as Maya Scene."""
import os
import itertools
import contextlib

from maya import cmds

from openpype.pipeline import publish
from openpype.hosts.maya.api import lib
from openpype.lib import (
    BoolDef
)


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


class ExtractCameraMayaScene(publish.Extractor,
                             publish.OptionalPyblishPluginMixin):
    """Extract a Camera as Maya Scene.

    This will create a duplicate of the camera that will be baked *with*
    substeps and handles for the required frames. This temporary duplicate
    will be published.

    The cameras gets baked to world space by default. Only when the instance's
    `bakeToWorldSpace` is set to False it will include its full hierarchy.

    'camera' family expects only single camera, if multiple cameras are needed,
    'matchmove' is better choice.

    Note:
        The extracted Maya ascii file gets "massaged" removing the uuid values
        so they are valid for older versions of Fusion (e.g. 6.4)

    """

    label = "Extract Camera (Maya Scene)"
    hosts = ["maya"]
    families = ["camera", "matchmove"]
    scene_type = "ma"

    keep_image_planes = True

    def process(self, instance):
        """Plugin entry point."""
        # get settings
        ext_mapping = (
            instance.context.data["project_settings"]["maya"]["ext_mapping"]
        )
        if ext_mapping:
            self.log.debug("Looking in settings for scene type ...")
            # use extension mapping for first family found
            for family in self.families:
                try:
                    self.scene_type = ext_mapping[family]
                    self.log.debug(
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
        members = set(cmds.ls(instance.data['setMembers'], leaf=True,
                      shapes=True, long=True, dag=True))
        cameras = set(cmds.ls(members, leaf=True, shapes=True, long=True,
                      dag=True, type="camera"))

        # validate required settings
        assert isinstance(step, float), "Step must be a float value"
        transforms = cmds.listRelatives(list(cameras),
                                        parent=True, fullPath=True)

        # Define extract output file path
        dir_path = self.staging_dir(instance)
        filename = "{0}.{1}".format(instance.name, self.scene_type)
        path = os.path.join(dir_path, filename)

        # Perform extraction
        with lib.maintained_selection():
            with lib.evaluation("off"):
                with lib.suspended_refresh():
                    if bake_to_worldspace:
                        baked = lib.bake_to_world_space(
                            transforms,
                            frame_range=[start, end],
                            step=step
                        )
                        baked_camera_shapes = set(cmds.ls(baked,
                                                  type="camera",
                                                  dag=True,
                                                  shapes=True,
                                                  long=True))

                        members.update(baked_camera_shapes)
                        members.difference_update(cameras)
                    else:
                        baked_camera_shapes = cmds.ls(list(cameras),
                                                      type="camera",
                                                      dag=True,
                                                      shapes=True,
                                                      long=True)

                    attrs = {"backgroundColorR": 0.0,
                             "backgroundColorG": 0.0,
                             "backgroundColorB": 0.0,
                             "overscan": 1.0}

                    # Fix PLN-178: Don't allow background color to be non-black
                    for cam, (attr, value) in itertools.product(cmds.ls(
                            baked_camera_shapes, type="camera", dag=True,
                            long=True), attrs.items()):
                        plug = "{0}.{1}".format(cam, attr)
                        unlock(plug)
                        cmds.setAttr(plug, value)

                    attr_values = self.get_attr_values_from_data(
                        instance.data)
                    keep_image_planes = attr_values.get("keep_image_planes")

                    with transfer_image_planes(sorted(cameras),
                                               sorted(baked_camera_shapes),
                                               keep_image_planes):

                        self.log.info("Performing extraction..")
                        cmds.select(cmds.ls(list(members), dag=True,
                                            shapes=True, long=True),
                                    noExpand=True)
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

        self.log.debug("Extracted instance '{0}' to: {1}".format(
            instance.name, path))

    @classmethod
    def get_attribute_defs(cls):
        defs = super(ExtractCameraMayaScene, cls).get_attribute_defs()

        defs.extend([
            BoolDef("keep_image_planes",
                    label="Keep Image Planes",
                    tooltip="Preserving connected image planes on camera",
                    default=cls.keep_image_planes),

        ])

        return defs


@contextlib.contextmanager
def transfer_image_planes(source_cameras, target_cameras,
                          keep_input_connections):
    """Reattaches image planes to baked or original cameras.

    Baked cameras are duplicates of original ones.
    This attaches it to duplicated camera properly and after
    export it reattaches it back to original to keep image plane in workfile.
    """
    originals = {}
    try:
        for source_camera, target_camera in zip(source_cameras,
                                                target_cameras):
            image_plane_plug = "{}.imagePlane".format(source_camera)
            image_planes = cmds.listConnections(image_plane_plug,
                                                source=True,
                                                destination=False,
                                                type="imagePlane") or []

            # Split of the parent path they are attached - we want
            # the image plane node name if attached to a camera.
            # TODO: Does this still mean the image plane name is unique?
            image_planes = [x.split("->", 1)[-1] for x in image_planes]

            if not image_planes:
                continue

            originals[source_camera] = []
            for image_plane in image_planes:
                if keep_input_connections:
                    if source_camera == target_camera:
                        continue
                    _attach_image_plane(target_camera, image_plane)
                else:  # explicitly detach image planes
                    cmds.imagePlane(image_plane, edit=True, detach=True)
                originals[source_camera].append(image_plane)
        yield
    finally:
        for camera, image_planes in originals.items():
            for image_plane in image_planes:
                _attach_image_plane(camera, image_plane)


def _attach_image_plane(camera, image_plane):
    cmds.imagePlane(image_plane, edit=True, detach=True)
    cmds.imagePlane(image_plane, edit=True, camera=camera)
