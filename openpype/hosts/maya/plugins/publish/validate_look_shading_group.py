from maya import cmds

import pyblish.api
import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishValidationError
)


class ValidateShadingEngine(pyblish.api.InstancePlugin):
    """Validate all shading engines are named after the surface material.

    Shading engines should be named "{surface_shader}SG"
    """

    order = ValidateContentsOrder
    families = ["look"]
    hosts = ["maya"]
    label = "Look Shading Engine Naming"
    actions = [
        openpype.hosts.maya.api.action.SelectInvalidAction, RepairAction
    ]

    # The default connections to check
    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                "Found shading engines with incorrect naming:"
                "\n{}".format(invalid)
            )

    @classmethod
    def get_invalid(cls, instance):
        shapes = cmds.ls(instance, type=["nurbsSurface", "mesh"], long=True)
        invalid = []
        for shape in shapes:
            shading_engines = cmds.listConnections(
                shape, destination=True, type="shadingEngine"
            ) or []
            for shading_engine in shading_engines:
                materials = cmds.listConnections(
                    shading_engine + ".surfaceShader",
                    source=True, destination=False
                )
                if not materials:
                    cls.log.warning(
                        "Shading engine '{}' has no material connected to its "
                        ".surfaceShader attribute.".format(shading_engine))
                    continue

                material = materials[0]  # there should only ever be one input
                name = material + "SG"
                if shading_engine != name:
                    invalid.append(shading_engine)

        return list(set(invalid))

    @classmethod
    def repair(cls, instance):
        shading_engines = cls.get_invalid(instance)
        for shading_engine in shading_engines:
            name = (
                cmds.listConnections(shading_engine + ".surfaceShader")[0]
                + "SG"
            )
            cmds.rename(shading_engine, name)
