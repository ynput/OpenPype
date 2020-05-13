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
    label = "ASS has relative texture paths"
    actions = [pype.api.RepairAction]

    def process(self, instance):
        # we cannot ask this until user open render settings as
        # `defaultArnoldRenderOptions` doesn't exists
        try:
            relative_texture = cmds.getAttr(
                "defaultArnoldRenderOptions.absolute_texture_paths")
            relative_procedural = cmds.getAttr(
                "defaultArnoldRenderOptions.absolute_procedural_paths")
            texture_search_path = cmds.getAttr(
                "defaultArnoldRenderOptions.tspath"
            )
            procedural_search_path = cmds.getAttr(
                "defaultArnoldRenderOptions.pspath"
            )
        except ValueError:
            assert False, ("Can not validate, render setting were not opened "
                           "yet so Arnold setting cannot be validate")

        scene_dir, scene_basename = os.path.split(cmds.file(q=True, loc=True))
        scene_name, _ = os.path.splitext(scene_basename)
        assert self.maya_is_true(relative_texture) is not True, \
            ("Texture path is set to be absolute")
        assert self.maya_is_true(relative_procedural) is not True, \
            ("Procedural path is set to be absolute")

        anatomy = instance.context.data["anatomy"]

        texture_search_path = texture_search_path.replace("\\", "/")
        procedural_search_path = procedural_search_path.replace("\\", "/")

        texture_success, texture_search_rootless_path = (
            anatomy.find_root_template_from_path(
                texture_search_path
            )
        )
        procedural_success, procedural_search_rootless_path = (
            anatomy.find_root_template_from_path(
                texture_search_path
            )
        )

        assert not texture_success, \
            ("Project root is not in texture_search_path")
        assert not procedural_success, \
            ("Project root is not in procedural_search_path")

    @classmethod
    def repair(cls, instance):
        texture_path = cmds.getAttr("defaultArnoldRenderOptions.tspath")
        procedural_path = cmds.getAttr("defaultArnoldRenderOptions.pspath")

        anatomy = instance.context.data["anatomy"]
        texture_success, texture_rootless_path = (
            anatomy.find_root_template_from_path(texture_path)
        )
        procedural_success, procedural_rootless_path = (
            anatomy.find_root_template_from_path(procedural_path)
        )

        all_root_paths = anatomy.all_root_paths()

        if not texture_success:
            final_path = cls.find_absolute_path(
                texture_rootless_path, all_root_paths
            )
            if final_path is None:
                raise AssertionError("Ass is loaded out of defined roots.")

            cmds.setAttr(
                "defaultArnoldRenderOptions.tspath",
                final_path,
                type="string"
            )
            cmds.setAttr(
                "defaultArnoldRenderOptions.absolute_texture_paths",
                False
            )

        if not procedural_success:
            final_path = cls.find_absolute_path(
                texture_rootless_path, all_root_paths
            )
            if final_path is None:
                raise AssertionError("Ass is loaded out of defined roots.")
            cmds.setAttr(
                "defaultArnoldRenderOptions.pspath",
                final_path,
                type="string"
            )
            cmds.setAttr(
                "defaultArnoldRenderOptions.absolute_procedural_paths",
                False
            )

    @staticmethod
    def find_absolute_path(relative_path, all_root_paths):
        for root_path in all_root_paths:
            possible_path = os.path.join(root_path, relative_path)
            if os.path.exists(possible_path):
                return possible_path

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
