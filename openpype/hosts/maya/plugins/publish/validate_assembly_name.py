import pyblish.api
import maya.cmds as cmds
import openpype.hosts.maya.api.action
from openpype.pipeline.publish import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)


class ValidateAssemblyName(pyblish.api.InstancePlugin,
                           OptionalPyblishPluginMixin):
    """ Ensure Assembly name ends with `GRP`

    Check if assembly name ends with `_GRP` string.
    """

    label = "Validate Assembly Name"
    order = pyblish.api.ValidatorOrder
    families = ["assembly"]
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    active = False
    optional = True

    @classmethod
    def get_invalid(cls, instance):
        cls.log.debug("Checking name of {}".format(instance.name))

        content_instance = instance.data.get("setMembers", None)
        if not content_instance:
            cls.log.error("Instance has no nodes!")
            return True

        # All children will be included in the extracted export so we also
        # validate *all* descendents of the set members and we skip any
        # intermediate shapes
        descendants = cmds.listRelatives(content_instance,
                                         allDescendents=True,
                                         fullPath=True) or []
        descendants = cmds.ls(
            descendants, noIntermediate=True, type="transform")
        content_instance = list(set(content_instance + descendants))
        assemblies = cmds.ls(content_instance, assemblies=True, long=True)

        invalid = []
        for cr in assemblies:
            if not cr.endswith('_GRP'):
                cls.log.error("{} doesn't end with _GRP".format(cr))
                invalid.append(cr)

        return invalid

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError("Found {} invalid named assembly "
                               "items".format(len(invalid)))
