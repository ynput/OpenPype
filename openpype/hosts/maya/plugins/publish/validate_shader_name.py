import re

import pyblish.api
from maya import cmds

import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin, PublishValidationError, ValidateContentsOrder)


class ValidateShaderName(pyblish.api.InstancePlugin,
                         OptionalPyblishPluginMixin):
    """Validate shader name assigned.

       It should be <assetName>_<*>_SHD

    """
    optional = True
    order = ValidateContentsOrder
    families = ["look"]
    hosts = ['maya']
    label = 'Validate Shaders Name'
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    regex = r'(?P<asset>.*)_(.*)_SHD'

    # The default connections to check
    def process(self, instance):
        if not self.is_active(instance.data):
            return

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                ("Found shapes with invalid shader names "
                 "assigned:\n{}").format(invalid))

    @classmethod
    def get_invalid(cls, instance):

        invalid = []

        # Get all shapes from the instance
        content_instance = instance.data.get("setMembers", None)
        if not content_instance:
            cls.log.error("Instance has no nodes!")
            return True
        pass
        descendants = cmds.listRelatives(content_instance,
                                         allDescendents=True,
                                         fullPath=True) or []

        descendants = cmds.ls(descendants, noIntermediate=True, long=True)
        shapes = cmds.ls(descendants, type=["nurbsSurface", "mesh"], long=True)
        asset_name = instance.data.get("asset")

        # Check the number of connected shadingEngines per shape
        regex_compile = re.compile(cls.regex)
        error_message = "object {0} has invalid shader name {1}"
        for shape in shapes:
            shading_engines = cmds.listConnections(shape,
                                                   destination=True,
                                                   type="shadingEngine") or []
            shaders = cmds.ls(
                cmds.listConnections(shading_engines), materials=1
            )

            for shader in shaders:
                m = regex_compile.match(shader)
                if m is None:
                    invalid.append(shape)
                    cls.log.error(error_message.format(shape, shader))
                else:
                    if 'asset' in regex_compile.groupindex:
                        if m.group('asset') != asset_name:
                            invalid.append(shape)
                            message = error_message
                            message += " with missing asset name \"{2}\""
                            cls.log.error(
                                message.format(shape, shader, asset_name)
                            )

        return invalid
