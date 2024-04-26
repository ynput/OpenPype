import os
import types

import maya.cmds as cmds
from mtoa.core import createOptions

import pyblish.api
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin
)


class ValidateAssRelativePaths(pyblish.api.InstancePlugin,
                               OptionalPyblishPluginMixin):
    """Ensure exporting ass file has set relative texture paths"""

    order = ValidateContentsOrder
    hosts = ['maya']
    families = ['ass']
    label = "ASS has relative texture paths"
    actions = [RepairAction]
    optional = False

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        # we cannot ask this until user open render settings as
        # `defaultArnoldRenderOptions` doesn't exist
        errors = []

        try:
            absolute_texture = cmds.getAttr(
                "defaultArnoldRenderOptions.absolute_texture_paths")
            absolute_procedural = cmds.getAttr(
                "defaultArnoldRenderOptions.absolute_procedural_paths")
            texture_search_path = cmds.getAttr(
                "defaultArnoldRenderOptions.tspath"
            )
            procedural_search_path = cmds.getAttr(
                "defaultArnoldRenderOptions.pspath"
            )
        except ValueError:
            raise PublishValidationError(
                "Default Arnold options has not been created yet."
            )

        scene_dir, scene_basename = os.path.split(cmds.file(q=True, loc=True))
        scene_name, _ = os.path.splitext(scene_basename)

        if self.maya_is_true(absolute_texture):
            errors.append("Texture path is set to be absolute")
        if self.maya_is_true(absolute_procedural):
            errors.append("Procedural path is set to be absolute")

        anatomy = instance.context.data["anatomy"]

        # Use project root variables for multiplatform support, see:
        # https://docs.arnoldrenderer.com/display/A5AFMUG/Search+Path
        # ':' as path separator is supported by Arnold for all platforms.
        keys = anatomy.root_environments().keys()
        paths = []
        for k in keys:
            paths.append("[{}]".format(k))

        self.log.debug("discovered roots: {}".format(":".join(paths)))

        if ":".join(paths) not in texture_search_path:
            errors.append((
                "Project roots {} are not in texture_search_path: {}"
            ).format(paths, texture_search_path))

        if ":".join(paths) not in procedural_search_path:
            errors.append((
                "Project roots {} are not in procedural_search_path: {}"
            ).format(paths, procedural_search_path))

        if errors:
            raise PublishValidationError("\n".join(errors))

    @classmethod
    def repair(cls, instance):
        createOptions()

        texture_path = cmds.getAttr("defaultArnoldRenderOptions.tspath")
        procedural_path = cmds.getAttr("defaultArnoldRenderOptions.pspath")

        # Use project root variables for multiplatform support, see:
        # https://docs.arnoldrenderer.com/display/A5AFMUG/Search+Path
        # ':' as path separator is supported by Arnold for all platforms.
        anatomy = instance.context.data["anatomy"]
        keys = anatomy.root_environments().keys()
        paths = []
        for k in keys:
            paths.append("[{}]".format(k))

        cmds.setAttr(
            "defaultArnoldRenderOptions.tspath",
            ":".join([p for p in paths + [texture_path] if p]),
            type="string"
        )
        cmds.setAttr(
            "defaultArnoldRenderOptions.absolute_texture_paths",
            False
        )

        cmds.setAttr(
            "defaultArnoldRenderOptions.pspath",
            ":".join([p for p in paths + [procedural_path] if p]),
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
        if isinstance(attr_val, bool):
            return attr_val
        elif isinstance(attr_val, (list, types.GeneratorType)):
            return any(attr_val)
        else:
            return bool(attr_val)
