import pyblish.api
import colorbleed.api


class ValidateAlembicInputNode(pyblish.api.InstancePlugin):
    """Validate that the node connected to the output is correct.

    The connected node cannot be of the following types for Alembic:
        - VDB
        - Volume

    """

    order = colorbleed.api.ValidateContentsOrder + 0.1
    families = ["pointcache"]
    hosts = ["houdini"]
    label = "Validate Input Node (Abc)"

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                "Primitive types found that are not supported"
                "for Alembic output."
            )

    @classmethod
    def get_invalid(cls, instance):

        invalid_prim_types = ["VDB", "Volume"]
        node = instance.data["output_node"]

        if not hasattr(node, "geometry"):
            # In the case someone has explicitly set an Object
            # node instead of a SOP node in Geometry context
            # then for now we ignore - this allows us to also
            # export object transforms.
            cls.log.warning("No geometry output node found, skipping check..")
            return

        frame = instance.data.get("frameStart", 0)
        geo = node.geometryAtFrame(frame)

        invalid = False
        for prim_type in invalid_prim_types:
            if geo.countPrimType(prim_type) > 0:
                cls.log.error(
                    "Found a primitive which is of type '%s' !" % prim_type
                )
                invalid = True

        if invalid:
            return [instance]
