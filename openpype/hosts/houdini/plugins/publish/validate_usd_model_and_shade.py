# -*- coding: utf-8 -*-
import pyblish.api

import openpype.hosts.houdini.api.usd as hou_usdlib
from openpype.pipeline import PublishValidationError

from pxr import UsdShade, UsdRender, UsdLux

import hou


def fullname(o):
    """Get fully qualified class name"""
    module = o.__module__
    if module is None or module == str.__module__:
        return o.__name__
    return module + "." + o.__name__


class ValidateUsdModel(pyblish.api.InstancePlugin):
    """Validate USD Model.

    Disallow Shaders, Render settings, products and vars and Lux lights.

    """

    order = pyblish.api.ValidatorOrder
    families = ["usdModel"]
    hosts = ["houdini"]
    label = "Validate USD Model"
    optional = True

    disallowed = [
        UsdShade.Shader,
        UsdRender.Settings,
        UsdRender.Product,
        UsdRender.Var,
        UsdLux.Light,
    ]

    def process(self, instance):

        rop = instance.data["transientData"]["instance_node"]
        lop_path = hou_usdlib.get_usd_rop_loppath(rop)
        stage = lop_path.stage(apply_viewport_overrides=False)

        invalid = []
        for prim in stage.Traverse():

            for klass in self.disallowed:
                if klass(prim):
                    # Get full class name without pxr. prefix
                    name = fullname(klass).split("pxr.", 1)[-1]
                    path = str(prim.GetPath())
                    self.log.warning("Disallowed %s: %s" % (name, path))

                    invalid.append(prim)

        if invalid:
            prim_paths = sorted([str(prim.GetPath()) for prim in invalid])
            raise PublishValidationError(
                "Found invalid primitives: {}".format(prim_paths))


class ValidateUsdShade(ValidateUsdModel):
    """Validate usdShade.

    Disallow Render settings, products, vars and Lux lights.

    """

    families = ["usdShade"]
    label = "Validate USD Shade"

    disallowed = [
        UsdRender.Settings,
        UsdRender.Product,
        UsdRender.Var,
        UsdLux.Light,
    ]
