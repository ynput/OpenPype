import pyblish.api
from openpype.pipeline.publish import ValidateContentsOrder


class ValidateCameraROP(pyblish.api.InstancePlugin):
    """Validate Camera ROP settings."""

    order = ValidateContentsOrder
    families = ["camera"]
    hosts = ["houdini"]
    label = "Camera ROP"

    def process(self, instance):

        import hou

        node = instance.data["members"][0]
        if node.parm("use_sop_path").eval():
            raise RuntimeError(
                "Alembic ROP for Camera export should not be "
                "set to 'Use Sop Path'. Please disable."
            )

        # Get the root and objects parameter of the Alembic ROP node
        root = node.parm("root").eval()
        objects = node.parm("objects").eval()
        assert root, "Root parameter must be set on Alembic ROP"
        assert root.startswith("/"), "Root parameter must start with slash /"
        assert objects, "Objects parameter must be set on Alembic ROP"
        assert len(objects.split(" ")) == 1, "Must have only a single object."

        # Check if the object exists and is a camera
        path = root + "/" + objects
        camera = hou.node(path)

        if not camera:
            raise ValueError("Camera path does not exist: %s" % path)

        if camera.type().name() != "cam":
            raise ValueError(
                "Object set in Alembic ROP is not a camera: "
                "%s (type: %s)" % (camera, camera.type().name())
            )
