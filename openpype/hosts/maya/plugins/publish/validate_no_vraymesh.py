import pyblish.api
from maya import cmds
from openpype.pipeline.publish import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)

def _as_report_list(values, prefix="- ", suffix="\n"):
    """Return list as bullet point list for a report"""
    if not values:
        return ""
    return prefix + (suffix + prefix).join(values)


class ValidateNoVRayMesh(pyblish.api.InstancePlugin,
                         OptionalPyblishPluginMixin):
    """Validate there are no VRayMesh objects in the instance"""

    order = pyblish.api.ValidatorOrder
    label = 'No V-Ray Proxies (VRayMesh)'
    families = ["pointcache"]
    optional = False

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        if not cmds.pluginInfo("vrayformaya", query=True, loaded=True):
            return

        shapes = cmds.ls(instance,
                         shapes=True,
                         type="mesh")

        inputs = cmds.listConnections(shapes,
                                      destination=False,
                                      source=True) or []
        vray_meshes = cmds.ls(inputs, type='VRayMesh')
        if vray_meshes:
            raise PublishValidationError(
                "Meshes that are V-Ray Proxies should not be in an Alembic "
                "pointcache.\n"
                "Found V-Ray proxies:\n\n{}".format(
                    _as_report_list(sorted(vray_meshes))
                ),
                title="V-Ray Proxies in pointcache"
            )
