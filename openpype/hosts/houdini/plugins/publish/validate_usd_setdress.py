# -*- coding: utf-8 -*-
import pyblish.api

import openpype.hosts.houdini.api.usd as hou_usdlib
from openpype.pipeline import PublishValidationError


class ValidateUsdSetDress(pyblish.api.InstancePlugin):
    """Validate USD Set Dress.

    Must only have references or payloads. May not generate new mesh or
    flattened meshes.

    """

    order = pyblish.api.ValidatorOrder
    families = ["usdSetDress"]
    hosts = ["houdini"]
    label = "Validate USD Set Dress"
    optional = True

    def process(self, instance):

        from pxr import UsdGeom
        import hou

        rop = instance.data["transientData"]["instance_node"]
        lop_path = hou_usdlib.get_usd_rop_loppath(rop)
        stage = lop_path.stage(apply_viewport_overrides=False)

        invalid = []
        for node in stage.Traverse():

            if UsdGeom.Mesh(node):
                # This solely checks whether there is any USD involved
                # in this Prim's Stack and doesn't accurately tell us
                # whether it was generated locally or not.
                # TODO: More accurately track whether the Prim was created
                #       in the local scene
                stack = node.GetPrimStack()
                for sdf in stack:
                    path = sdf.layer.realPath
                    if path:
                        break
                else:
                    prim_path = node.GetPath()
                    self.log.error(
                        "%s is not referenced geometry." % prim_path
                    )
                    invalid.append(node)

        if invalid:
            raise PublishValidationError((
                "SetDress contains local geometry. "
                "This is not allowed, it must be an assembly "
                "of referenced assets."),
                title=self.label
            )
