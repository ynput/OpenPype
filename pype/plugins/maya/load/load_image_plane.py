from avalon import api
from Qt import QtWidgets


class ImagePlaneLoader(api.Loader):
    """Specific loader of plate for image planes on selected camera."""

    families = ["plate", "render"]
    label = "Create imagePlane on selected camera."
    representations = ["mov", "exr"]
    icon = "image"
    color = "orange"

    def load(self, context, name, namespace, data):
        import pymel.core as pc

        new_nodes = []
        image_plane_depth = 1000

        # Getting camera from selection.
        selection = pc.ls(selection=True)

        if len(selection) > 1:
            QtWidgets.QMessageBox.critical(
                None,
                "Error!",
                "Multiple nodes selected. Please select only one.",
                QtWidgets.QMessageBox.Ok
            )
            return

        if len(selection) < 1:
            QtWidgets.QMessageBox.critical(
                None,
                "Error!",
                "No camera selected.",
                QtWidgets.QMessageBox.Ok
            )
            return

        relatives = pc.listRelatives(selection[0], shapes=True)
        if not pc.ls(relatives, type="camera"):
            QtWidgets.QMessageBox.critical(
                None,
                "Error!",
                "Selected node is not a camera.",
                QtWidgets.QMessageBox.Ok
            )
            return

        camera = selection[0]

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
        image_plane_shape.useFrameExtension.set(1)

        if context["representation"]["name"] == "mov":
            # Need to get "type" by string, because its a method as well.
            pc.Attribute(image_plane_shape + ".type").set(2)

        # Ask user whether to use sequence or still image.
        if context["representation"]["name"] == "exr":
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

            # Ensure OpenEXRLoader plugin is loaded.
            pc.loadPlugin("OpenEXRLoader.mll", quiet=True)

        new_nodes.extend(
            [image_plane_transform.name(), image_plane_shape.name()]
        )

        return new_nodes
