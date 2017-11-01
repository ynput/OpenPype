import pyblish.api
import colorbleed.api


class ValidateSingleAssembly(pyblish.api.InstancePlugin):
    """Ensure the content of the instance is grouped in a single hierarchy

    The instance must have a node which resides within the a group which
    is visible in the outliner.
    Example outliner:
        root_GRP
            -- asset_001_GRP
               -- asset_01_:rigDefault
            -- asset_001_GRP
               -- asset_01_:rigDefault

    """

    order = colorbleed.api.ValidateContentsOrder
    hosts = ['maya']
    families = ['colorbleed.rig', 'colorbleed.animation']
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
