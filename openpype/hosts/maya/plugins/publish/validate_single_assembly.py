import pyblish.api

from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    ValidateContentsOrder,
)


class ValidateSingleAssembly(pyblish.api.InstancePlugin,
                             OptionalPyblishPluginMixin):
    """Ensure the content of the instance is grouped in a single hierarchy

    The instance must have a single root node containing all the content.
    This root node *must* be a top group in the outliner.

    Example outliner:
        root_GRP
            -- geometry_GRP
               -- mesh_GEO
            -- controls_GRP
               -- control_CTL

    """

    order = ValidateContentsOrder
    hosts = ['maya']
    families = ['rig']
    label = 'Single Assembly'

    def process(self, instance):
        from maya import cmds

        assemblies = cmds.ls(instance, assemblies=True)

        # ensure unique (somehow `maya.cmds.ls` doesn't manage that)
        assemblies = set(assemblies)

        assert len(assemblies) > 0, (
            "One assembly required for: %s (currently empty?)" % instance)
        assert len(assemblies) < 2, (
            'Multiple assemblies found: %s' % assemblies)
