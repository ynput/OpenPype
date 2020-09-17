import pymel.core as pc
import maya.cmds as cmds

from avalon import api
from avalon.maya.pipeline import containerise
from avalon.maya import lib
from Qt import QtWidgets


class ImagePlaneLoader(api.Loader):
    """Specific loader of plate for image planes on selected camera."""

    families = ["plate", "render"]
    label = "Create imagePlane on selected camera."
    representations = ["mov", "exr", "preview", "png"]
    icon = "image"
    color = "orange"

    def load(self, context, name, namespace, data):
        new_nodes = []
        image_plane_depth = 1000
        asset = context['asset']['name']
        namespace = namespace or lib.unique_namespace(
            asset + "_",
            prefix="_" if asset[0].isdigit() else "",
            suffix="_",
        )

        # Getting camera from selection.
        selection = pc.ls(selection=True)

        camera = None

        if len(selection) > 1:
            QtWidgets.QMessageBox.critical(
                None,
                "Error!",
                "Multiple nodes selected. Please select only one.",
                QtWidgets.QMessageBox.Ok
            )
            return

        if len(selection) < 1:
            result = QtWidgets.QMessageBox.critical(
                None,
                "Error!",
                "No camera selected. Do you want to create a camera?",
                QtWidgets.QMessageBox.Ok,
                QtWidgets.QMessageBox.Cancel
            )
            if result == QtWidgets.QMessageBox.Ok:
                camera = pc.createNode("camera")
            else:
                return
        else:
            relatives = pc.listRelatives(selection[0], shapes=True)
            if pc.ls(relatives, type="camera"):
                camera = selection[0]
            else:
                QtWidgets.QMessageBox.critical(
                    None,
                    "Error!",
                    "Selected node is not a camera.",
                    QtWidgets.QMessageBox.Ok
                )
                return

        try:
            camera.displayResolution.set(1)
            camera.farClipPlane.set(image_plane_depth * 10)
        except RuntimeError:
            pass

        # Create image plane
        image_plane_transform, image_plane_shape = pc.imagePlane(
            camera=camera, showInAllViews=False
        )
        image_plane_shape.depth.set(image_plane_depth)

        image_plane_shape.imageName.set(
            context["representation"]["data"]["path"]
        )

        start_frame = pc.playbackOptions(q=True, min=True)
        end_frame = pc.playbackOptions(q=True, max=True)

        image_plane_shape.frameOffset.set(1 - start_frame)
        image_plane_shape.frameIn.set(start_frame)
        image_plane_shape.frameOut.set(end_frame)
        image_plane_shape.frameCache.set(end_frame)
        image_plane_shape.useFrameExtension.set(1)

        movie_representations = ["mov", "preview"]
        if context["representation"]["name"] in movie_representations:
            # Need to get "type" by string, because its a method as well.
            pc.Attribute(image_plane_shape + ".type").set(2)

        # Ask user whether to use sequence or still image.
        if context["representation"]["name"] == "exr":
            # Ensure OpenEXRLoader plugin is loaded.
            pc.loadPlugin("OpenEXRLoader.mll", quiet=True)

            reply = QtWidgets.QMessageBox.information(
                None,
                "Frame Hold.",
                "Hold image sequence on first frame?",
                QtWidgets.QMessageBox.Ok,
                QtWidgets.QMessageBox.Cancel
            )
            if reply == QtWidgets.QMessageBox.Ok:
                pc.delete(
                    image_plane_shape.listConnections(type="expression")[0]
                )
                image_plane_shape.frameExtension.set(start_frame)

        new_nodes.extend(
            [
                image_plane_transform.longName().split("|")[-1],
                image_plane_shape.longName().split("|")[-1]
            ]
        )

        for node in new_nodes:
            pc.rename(node, "{}:{}".format(namespace, node))

        return containerise(
            name=name,
            namespace=namespace,
            nodes=new_nodes,
            context=context,
            loader=self.__class__.__name__
        )

    def update(self, container, representation):
        image_plane_shape = None
        for node in pc.PyNode(container["objectName"]).members():
            if node.nodeType() == "imagePlane":
                image_plane_shape = node

        assert image_plane_shape is not None, "Image plane not found."

        path = api.get_representation_path(representation)
        image_plane_shape.imageName.set(path)
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
