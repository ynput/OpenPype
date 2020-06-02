from maya import cmds

import pyblish.api
import pype.api
import pype.hosts.maya.action
import re


class ValidateShaderName(pyblish.api.InstancePlugin):
    """Validate shader name assigned.

       It should be <assetName>_<*>_SHD

    """
    optional = True
    active = False
    order = pype.api.ValidateContentsOrder
    families = ["look"]
    hosts = ['maya']
    label = 'Validate Shaders Name'
    actions = [pype.hosts.maya.action.SelectInvalidAction]
    regex = r'(?P<asset>.*)_(.*)_SHD'

    # The default connections to check
    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Found shapes with invalid shader names "
                               "assigned: "
                               "\n{}".format(invalid))

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
        asset_name = instance.data.get("asset", None)

        # Check the number of connected shadingEngines per shape
        r = re.compile(cls.regex)
        for shape in shapes:
            shading_engines = cmds.listConnections(shape,
                                                   destination=True,
                                                   type="shadingEngine") or []
            shaders = cmds.ls(
                cmds.listConnections(shading_engines), materials=1
            )

            for shader in shaders:
                m = r.match(cls.regex, shader)
                if m is None:
                    invalid.append(shape)
                    cls.log.error(
                        "object {0} has invalid shader name {1}".format(shape,
                                                                        shader)
                    )
                else:
                    if 'asset' in r.groupindex:
                        if m.group('asset') != asset_name:
                            invalid.append(shape)
                            cls.log.error(("object {0} has invalid "
                                           "shader name {1}").format(shape,
                                                                     shader))

        return invalid
