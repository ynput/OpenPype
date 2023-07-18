# -*- coding: utf-8 -*-
import pyblish.api

from collections import defaultdict
from openpype.pipeline import PublishValidationError


class ValidateReviewColorspace(pyblish.api.InstancePlugin):
    """Validate Review Colorspace parameters.


    """

    order = pyblish.api.ValidatorOrder + 0.1
    families = ["review"]
    hosts = ["houdini"]
    label = "Validate Review Colorspace"

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                ("Colorspace parameter is not valid."),
                title=self.label
            )

    @classmethod
    def get_invalid(cls, instance):
        import hou  # noqa
        output_node = instance.data.get("output_node")
        rop_node = hou.node(instance.data["instance_node"])
        if output_node is None:
            cls.log.error(
                "SOP Output node in '%s' does not exist. "
                "Ensure a valid SOP output path is set." % rop_node.path()
            )

            return [rop_node.path()]

        pattern = rop_node.parm("prim_to_detail_pattern").eval().strip()
        if not pattern:
            cls.log.debug(
                "Alembic ROP has no 'Primitive to Detail' pattern. "
                "Validation is ignored.."
            )
            return

        build_from_path = rop_node.parm("build_from_path").eval()
        if not build_from_path:
            cls.log.debug(
                "Alembic ROP has 'Build from Path' disabled. "
                "Validation is ignored.."
            )
            return

        path_attr = rop_node.parm("path_attrib").eval()
        if not path_attr:
            cls.log.error(
                "The Alembic ROP node has no Path Attribute"
                "value set, but 'Build Hierarchy from Attribute'"
                "is enabled."
            )
            return [rop_node.path()]

        # Let's assume each attribute is explicitly named for now and has no
        # wildcards for Primitive to Detail. This simplifies the check.
        cls.log.debug("Checking Primitive to Detail pattern: %s" % pattern)
        cls.log.debug("Checking with path attribute: %s" % path_attr)

        if not hasattr(output_node, "geometry"):
            # In the case someone has explicitly set an Object
            # node instead of a SOP node in Geometry context
            # then for now we ignore - this allows us to also
            # export object transforms.
            cls.log.warning("No geometry output node found, skipping check..")
            return

        # Check if the primitive attribute exists
        frame = instance.data.get("frameStart", 0)
        geo = output_node.geometryAtFrame(frame)

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
            return [output_node.path()]

        # Ensure at least a single string value is present
        if not attrib.strings():
            cls.log.info(
                "Primitive path attribute has no "
                "string values: %s" % path_attr
            )
            return [output_node.path()]

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
                    return [output_node.path()]
