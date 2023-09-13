# -*- coding: utf-8 -*-
"""Validator plugin for Houdini Camera ROP settings."""
import pyblish.api
from openpype.pipeline import PublishValidationError


class ValidateCameraROP(pyblish.api.InstancePlugin):
    """Validate Camera ROP settings."""

    order = pyblish.api.ValidatorOrder
    families = ["camera"]
    hosts = ["houdini"]
    label = "Camera ROP"

    def process(self, instance):

        import hou

        node = instance.data["transientData"]["instance_node"]
        if node.parm("use_sop_path").eval():
            raise PublishValidationError(
                ("Alembic ROP for Camera export should not be "
                 "set to 'Use Sop Path'. Please disable."),
                title=self.label
            )

        # Get the root and objects parameter of the Alembic ROP node
        root = node.parm("root").eval()
        objects = node.parm("objects").eval()
        errors = []
        if not root:
            errors.append("Root parameter must be set on Alembic ROP")
        if not root.startswith("/"):
            errors.append("Root parameter must start with slash /")
        if not objects:
            errors.append("Objects parameter must be set on Alembic ROP")
        if len(objects.split(" ")) != 1:
            errors.append("Must have only a single object.")

        if errors:
            for error in errors:
                self.log.error(error)
            raise PublishValidationError(
                "Some checks failed, see validator log.",
                title=self.label)

        # Check if the object exists and is a camera
        path = root + "/" + objects
        camera = hou.node(path)

        if not camera:
            raise PublishValidationError(
                "Camera path does not exist: %s" % path,
                title=self.label)

        if camera.type().name() != "cam":
            raise PublishValidationError(
                ("Object set in Alembic ROP is not a camera: "
                 "{} (type: {})").format(camera, camera.type().name()),
                title=self.label)
