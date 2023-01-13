from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.lib import EnumDef
from openpype.hosts.maya.api.pipeline import containerise
from openpype.hosts.maya.api.lib import (
    unique_namespace,
    namespaced
)

from maya import cmds


def create_texture():
    """Create place2dTexture with file node with uv connections

    Mimics Maya "file [Texture]" creation.
    """

    place = cmds.shadingNode("place2dTexture", asUtility=True, name="place2d")
    file = cmds.shadingNode("file", asTexture=True, name="file")

    connections = ["coverage", "translateFrame", "rotateFrame", "rotateUV",
                   "mirrorU", "mirrorV", "stagger", "wrapV", "wrapU",
                   "repeatUV", "offset", "noiseUV", "vertexUvThree",
                   "vertexUvTwo", "vertexUvOne", "vertexCameraOne"]
    for attr in connections:
        src = "{}.{}".format(place, attr)
        dest = "{}.{}".format(file, attr)
        cmds.connectAttr(src, dest)

    cmds.connectAttr(place + '.outUV', file + '.uvCoord')
    cmds.connectAttr(place + '.outUvFilterSize', file + '.uvFilterSize')

    return file, place


def create_projection():
    """Create texture with place3dTexture and projection

    Mimics Maya "file [Projection]" creation.
    """

    file, place = create_texture()
    projection = cmds.shadingNode("projection", asTexture=True,
                                  name="projection")
    place3d = cmds.shadingNode("place3dTexture", asUtility=True,
                               name="place3d")

    cmds.connectAttr(place3d + '.worldInverseMatrix[0]',
                     projection + ".placementMatrix")
    cmds.connectAttr(file + '.outColor', projection + ".image")

    return file, place, projection, place3d


def create_stencil():
    """Create texture with extra place2dTexture offset and stencil

    Mimics Maya "file [Stencil]" creation.
    """

    file, place = create_texture()

    place_stencil = cmds.shadingNode("place2dTexture", asUtility=True,
                                     name="place2d_stencil")
    stencil = cmds.shadingNode("stencil", asTexture=True, name="stencil")

    for src_attr, dest_attr in [
        ("outUV", "uvCoord"),
        ("outUvFilterSize", "uvFilterSize")
    ]:
        src_plug = "{}.{}".format(place_stencil, src_attr)
        cmds.connectAttr(src_plug, "{}.{}".format(place, dest_attr))
        cmds.connectAttr(src_plug, "{}.{}".format(stencil, dest_attr))

    return file, place, stencil, place_stencil


class FileNodeLoader(load.LoaderPlugin):
    """File node loader."""
    # TODO: Implement color space manamagent OCIO (set correct color space)

    families = ["image", "plate", "render"]
    label = "Load file node"
    representations = ["exr", "tif", "png", "jpg"]
    icon = "image"
    color = "orange"
    order = 2

    options = [
        EnumDef(
            "mode",
            items={
                "texture": "Texture",
                "projection": "Projection",
                "stencil": "Stencil"
            },
            default="texture",
            label="Texture Mode"
        )
    ]

    def load(self, context, name, namespace, data):

        path = self.fname
        asset = context['asset']['name']
        namespace = namespace or unique_namespace(
            asset + "_",
            prefix="_" if asset[0].isdigit() else "",
            suffix="_",
        )

        with namespaced(namespace, new=True) as namespace:
            # Create the nodes within the namespace
            nodes = {
                "texture": create_texture,
                "projection": create_projection,
                "stencil": create_stencil
            }[data.get("mode", "texture")]()

            # Set the file node attributes
            file_node = cmds.ls(nodes, type="file")[0]
            cmds.setAttr(file_node + ".fileTextureName", path, type="string")

            # Set UV tiling mode if UDIM tiles
            # TODO: Detect UDIM tiles and set accordingly (also on update)
            cmds.setAttr(file_node + ".uvTilingMode", 3)    # UDIM-tiles

            # Enable sequence if publish has `startFrame` and `endFrame` and
            # `startFrame != endFrame`
            # TODO: Detect sequences (also on update)
            # cmds.setAttr(file_node + ".useFrameExtension", True)

            # For ease of access for the user select all the nodes and select
            # the file node last so that UI shows its attributes by default
            cmds.select(list(nodes) + [file_node], replace=True)

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__
        )

    def update(self, container, representation):

        path = get_representation_path(representation)
        members = cmds.sets(container['objectName'], query=True)

        file_node = cmds.ls(members, type="file")[0]
        cmds.setAttr(file_node + ".fileTextureName", path, type="string")

        # Update representation
        cmds.setAttr(
            container["objectName"] + ".representation",
            str(representation["_id"]),
            type="string"
        )

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        members = cmds.sets(container['objectName'], query=True)
        cmds.lockNode(members, lock=False)
        cmds.delete([container['objectName']] + members)

        # Clean up the namespace
        try:
            cmds.namespace(removeNamespace=container['namespace'],
                           deleteNamespaceContent=True)
        except RuntimeError:
            pass
