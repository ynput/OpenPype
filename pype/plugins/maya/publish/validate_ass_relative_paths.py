import os
import types

import maya.cmds as cmds

import pyblish.api
import pype.api
import pype.maya.action


class ValidateAssRelativePaths(pyblish.api.InstancePlugin):
    """Ensure exporting ass file has set relative texture paths"""

    order = pype.api.ValidateContentsOrder
    hosts = ['maya']
    families = ['ass']
    label = "Validate ASS has relative texture paths"
    actions = [pype.api.RepairAction]

    def process(self, instance):
        # we cannot ask this until user open render settings as
        # `defaultArnoldRenderOptions` doesn't exists
        try:
            relative_texture = cmds.getAttr(
                "defaultArnoldRenderOptions.absolute_procedural_paths")
            texture_search_path = cmds.getAttr(
                "defaultArnoldRenderOptions.tspath"
            )
        except ValueError:
            assert False, ("Can not validate, render setting were not opened "
                           "yet so Arnold setting cannot be validate")

        scene_dir, scene_basename = os.path.split(cmds.file(q=True, loc=True))
        scene_name, _ = os.path.splitext(scene_basename)
        project_root = "{}{}{}{}".format(
            os.environ.get("AVALON_PROJECTS"),
            os.path.sep,
            os.environ.get("AVALON_PROJECT"),
            os.pathsep
        )
        assert self.maya_is_true(relative_texture) is not True, \
            ("Texture path are set to be absolute")

        texture_search_path.replace("\\", "/")
        assert project_root in texture_search_path, \
            ("Project root is not in texture_search_path")

    @classmethod
    def repair(cls, instance):
        texture_search_path = cmds.getAttr(
            "defaultArnoldRenderOptions.tspath"
        )
        project_root = "{}{}{}{}".format(
            os.environ.get("AVALON_PROJECTS"),
            os.path.sep,
            os.environ.get("AVALON_PROJECT"),
            os.pathsep
        )

        project_root = project_root.replace("\\", "/")
        cmds.setAttr("defaultArnoldRenderOptions.tspath",
                     project_root + texture_search_path,
                     type="string")
        cmds.setAttr("defaultArnoldRenderOptions.absolute_procedural_paths",
                     False)

    def maya_is_true(self, attr_val):
        """
        Whether a Maya attr evaluates to True.
        When querying an attribute value from an ambiguous object the
        Maya API will return a list of values, which need to be properly
        handled to evaluate properly.
        """
        if isinstance(attr_val, types.BooleanType):
            return attr_val
        elif isinstance(attr_val, (types.ListType, types.GeneratorType)):
            return any(attr_val)
        else:
            return bool(attr_val)
