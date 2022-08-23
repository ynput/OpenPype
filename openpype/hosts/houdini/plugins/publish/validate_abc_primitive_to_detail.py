import pyblish.api
import openpype.api

from collections import defaultdict


class ValidateAbcPrimitiveToDetail(pyblish.api.InstancePlugin):
    """Validate Alembic ROP Primitive to Detail attribute is consistent.

    The Alembic ROP crashes Houdini whenever an attribute in the "Primitive to
    Detail" parameter exists on only a part of the primitives that belong to
    the same hierarchy path. Whenever it encounters inconsistent values,
    specifically where some are empty as opposed to others then Houdini
    crashes. (Tested in Houdini 17.5.229)

    """

    order = openpype.api.ValidateContentsOrder + 0.1
    families = ["pointcache"]
    hosts = ["houdini"]
    label = "Validate Primitive to Detail (Abc)"

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                "Primitives found with inconsistent primitive "
                "to detail attributes. See log."
            )

    @classmethod
    def get_invalid(cls, instance):

        output = instance.data["output_node"]

        rop = instance[0]
        pattern = rop.parm("prim_to_detail_pattern").eval().strip()
        if not pattern:
            cls.log.debug(
                "Alembic ROP has no 'Primitive to Detail' pattern. "
                "Validation is ignored.."
            )
            return

        build_from_path = rop.parm("build_from_path").eval()
        if not build_from_path:
            cls.log.debug(
                "Alembic ROP has 'Build from Path' disabled. "
                "Validation is ignored.."
            )
            return

        path_attr = rop.parm("path_attrib").eval()
        if not path_attr:
            cls.log.error(
                "The Alembic ROP node has no Path Attribute"
                "value set, but 'Build Hierarchy from Attribute'"
                "is enabled."
            )
            return [rop.path()]

        # Let's assume each attribute is explicitly named for now and has no
        # wildcards for Primitive to Detail. This simplifies the check.
        cls.log.debug("Checking Primitive to Detail pattern: %s" % pattern)
        cls.log.debug("Checking with path attribute: %s" % path_attr)

        # Check if the primitive attribute exists
        frame = instance.data.get("frameStart", 0)
        geo = output.geometryAtFrame(frame)

        # If there are no primitives on the start frame then it might be
        # something that is emitted over time. As such we can't actually
        # validate whether the attributes exist, because they won't exist
        # yet. In that case, just warn the user and allow it.
        if len(geo.iterPrims()) == 0:
            cls.log.warning(
                "No primitives found on current frame. Validation"
                " for Primitive to Detail will be skipped."
            )
            return

        attrib = geo.findPrimAttrib(path_attr)
        if not attrib:
            cls.log.info(
                "Geometry Primitives are missing "
                "path attribute: `%s`" % path_attr
            )
            return [output.path()]

        # Ensure at least a single string value is present
        if not attrib.strings():
            cls.log.info(
                "Primitive path attribute has no "
                "string values: %s" % path_attr
            )
            return [output.path()]

        paths = None
        for attr in pattern.split(" "):
            if not attr.strip():
                # Ignore empty values
                continue

            # Check if the primitive attribute exists
            attrib = geo.findPrimAttrib(attr)
            if not attrib:
                # It is allowed to not have the attribute at all
                continue

            # The issue can only happen if at least one string attribute is
            # present. So we ignore cases with no values whatsoever.
            if not attrib.strings():
                continue

            check = defaultdict(set)
            values = geo.primStringAttribValues(attr)
            if paths is None:
                paths = geo.primStringAttribValues(path_attr)

            for path, value in zip(paths, values):
                check[path].add(value)

            for path, values in check.items():
                # Whenever a single path has multiple values for the
                # Primitive to Detail attribute then we consider it
                # inconsistent and invalidate the ROP node's content.
                if len(values) > 1:
                    cls.log.warning(
                        "Path has multiple values: %s (path: %s)"
                        % (list(values), path)
                    )
                    return [output.path()]
