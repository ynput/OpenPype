import pyblish.api
import openpype.api


class ValidatePrimitiveHierarchyPaths(pyblish.api.InstancePlugin):
    """Validate all primitives build hierarchy from attribute when enabled.

    The name of the attribute must exist on the prims and have the same name
    as Build Hierarchy from Attribute's `Path Attribute` value on the Alembic
    ROP node whenever Build Hierarchy from Attribute is enabled.

    """

    order = openpype.api.ValidateContentsOrder + 0.1
    families = ["pointcache"]
    hosts = ["houdini"]
    label = "Validate Prims Hierarchy Path"

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("See log for details. "
                               "Invalid nodes: {0}".format(invalid))

    @classmethod
    def get_invalid(cls, instance):

        import hou

        output = instance.data["output_node"]
        prims = output.geometry().prims()

        rop = instance[0]
        build_from_path = rop.parm("build_from_path").eval()
        if not build_from_path:
            cls.log.debug("Alembic ROP has 'Build from Path' disabled. "
                          "Validation is ignored..")
            return

        path_attr = rop.parm("path_attrib").eval()
        if not path_attr:
            cls.log.error("The Alembic ROP node has no Path Attribute"
                          "value set, but 'Build Hierarchy from Attribute'"
                          "is enabled.")
            return [rop.path()]

        cls.log.debug("Checking for attribute: %s" % path_attr)

        missing_attr = []
        invalid_attr = []
        for prim in prims:

            try:
                path = prim.stringAttribValue(path_attr)
            except hou.OperationFailed:
                # Attribute does not exist.
                missing_attr.append(prim)
                continue

            if not path:
                # Empty path value is invalid.
                invalid_attr.append(prim)
                continue

        if missing_attr:
            cls.log.info("Prims are missing attribute `%s`" % path_attr)

        if invalid_attr:
            cls.log.info("Prims have no value for attribute `%s` "
                         "(%s of %s prims)" % (path_attr,
                                      len(invalid_attr),
                                      len(prims)))

        if missing_attr or invalid_attr:
            return [output.path()]
