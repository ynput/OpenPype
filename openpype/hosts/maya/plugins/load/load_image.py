import os
import copy

from openpype.lib import EnumDef
from openpype.pipeline import (
    load,
    get_representation_context,
    get_current_host_name,
)
from openpype.pipeline.load.utils import get_representation_path_from_context
from openpype.pipeline.colorspace import (
    get_imageio_file_rules_colorspace_from_filepath,
    get_imageio_config,
    get_imageio_file_rules
)
from openpype.settings import get_project_settings

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

        file_node = cmds.ls(nodes, type="file")[0]

        self._apply_representation_context(context, file_node)

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

        members = cmds.sets(container['objectName'], query=True)
        file_node = cmds.ls(members, type="file")[0]

        context = get_representation_context(representation)
        self._apply_representation_context(context, file_node)

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

    def _apply_representation_context(self, context, file_node):
        """Update the file node to match the context.

        This sets the file node's attributes for:
            - file path
            - udim tiling mode (if it is an udim tile)
            - use frame extension (if it is a sequence)
            - colorspace

        """

        repre_context = context["representation"]["context"]
        has_frames = repre_context.get("frame") is not None
        has_udim = repre_context.get("udim") is not None

        # Set UV tiling mode if UDIM tiles
        if has_udim:
            cmds.setAttr(file_node + ".uvTilingMode", 3)    # UDIM-tiles
        else:
            cmds.setAttr(file_node + ".uvTilingMode", 0)    # off

        # Enable sequence if publish has `startFrame` and `endFrame` and
        # `startFrame != endFrame`
        if has_frames and self._is_sequence(context):
            # When enabling useFrameExtension maya automatically
            # connects an expression to <file>.frameExtension to set
            # the current frame. However, this expression  is generated
            # with some delay and thus it'll show a warning if frame 0
            # doesn't exist because we're explicitly setting the <f>
            # token.
            cmds.setAttr(file_node + ".useFrameExtension", True)
        else:
            cmds.setAttr(file_node + ".useFrameExtension", False)

        # Set the file node path attribute
        path = self._format_path(context)
        cmds.setAttr(file_node + ".fileTextureName", path, type="string")

        # Set colorspace
        colorspace = self._get_colorspace(context)
        if colorspace:
            cmds.setAttr(file_node + ".colorSpace", colorspace, type="string")
        else:
            self.log.debug("Unknown colorspace - setting colorspace skipped.")

    def _is_sequence(self, context):
        """Check whether frameStart and frameEnd are not the same."""
        version = context.get("version", {})
        representation = context.get("representation", {})

        for doc in [representation, version]:
            # Frame range can be set on version or representation.
            # When set on representation it overrides version data.
            data = doc.get("data", {})
            start = data.get("frameStartHandle", data.get("frameStart", None))
            end = data.get("frameEndHandle", data.get("frameEnd", None))

            if start is None or end is None:
                continue

            if start != end:
                return True
            else:
                return False

        return False

    def _get_colorspace(self, context):
        """Return colorspace of the file to load.

        Retrieves the explicit colorspace from the publish. If no colorspace
        data is stored with published content then project imageio settings
        are used to make an assumption of the colorspace based on the file
        rules. If no file rules match then None is returned.

        Returns:
            str or None: The colorspace of the file or None if not detected.

        """

        # We can't apply color spaces if management is not enabled
        if not cmds.colorManagementPrefs(query=True, cmEnabled=True):
            return

        representation = context["representation"]
        colorspace_data = representation.get("data", {}).get("colorspaceData")
        if colorspace_data:
            return colorspace_data["colorspace"]

        # Assume colorspace from filepath based on project settings
        project_name = context["project"]["name"]
        host_name = get_current_host_name()
        project_settings = get_project_settings(project_name)

        config_data = get_imageio_config(
            project_name, host_name,
            project_settings=project_settings
        )

        # ignore if host imageio is not enabled
        if not config_data:
            return

        file_rules = get_imageio_file_rules(
            project_name, host_name,
            project_settings=project_settings
        )

        path = get_representation_path_from_context(context)
        colorspace = get_imageio_file_rules_colorspace_from_filepath(
            path,
            host_name,
            project_name,
            config_data=config_data,
            file_rules=file_rules,
            project_settings=project_settings
        )

        return colorspace

    def _format_path(self, context):
        """Format the path with correct tokens for frames and udim tiles."""

        context = copy.deepcopy(context)
        representation = context["representation"]
        template = representation.get("data", {}).get("template")
        if not template:
            # No template to find token locations for
            return get_representation_path_from_context(context)

        def _placeholder(key):
            # Substitute with a long placeholder value so that potential
            # custom formatting with padding doesn't find its way into
            # our formatting, so that <f> wouldn't be padded as 0<f>
            return "___{}___".format(key)

        # We format UDIM and Frame numbers with their specific tokens. To do so
        # we in-place change the representation context data to format the path
        # with our own data
        tokens = {
            "frame": "<f>",
            "udim": "<UDIM>"
        }
        has_tokens = False
        repre_context = representation["context"]
        for key, _token in tokens.items():
            if key in repre_context:
                repre_context[key] = _placeholder(key)
                has_tokens = True

        # Replace with our custom template that has the tokens set
        representation["data"]["template"] = template
        path = get_representation_path_from_context(context)

        if has_tokens:
            for key, token in tokens.items():
                if key in repre_context:
                    path = path.replace(_placeholder(key), token)

        return path
