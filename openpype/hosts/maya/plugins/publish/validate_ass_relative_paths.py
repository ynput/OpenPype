# -*- coding: utf-8 -*-
"""Ensure exporting ass file has set relative texture paths."""
import os
import types

import maya.cmds as cmds

import pyblish.api
from pyblish.api import Instance
import openpype.api
import openpype.hosts.maya.api.action
from openpype.pipeline import PublishXmlValidationError


class ValidateAssRelativePaths(pyblish.api.InstancePlugin):
    """Ensure exporting ass file has set relative texture paths"""

    order = openpype.api.ValidateContentsOrder
    hosts = ['maya']
    families = ['ass']
    label = "ASS has relative texture paths"
    actions = [openpype.api.RepairAction]

    def process(self, instance):
        # type: (Instance) -> None
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
            raise PublishXmlValidationError(
                self, "Render Settings were not opened.")

        scene_dir, scene_basename = os.path.split(cmds.file(q=True, loc=True))
        scene_name, _ = os.path.splitext(scene_basename)
        if self.maya_is_true(relative_texture) is True:
            raise PublishXmlValidationError(
                self, "Texture path is set to be absolute.",
                key="texture_paths_not_relative")
        if self.maya_is_true(relative_procedural) is True:
            raise PublishXmlValidationError(
                self, "Procedural path is set to be absolute.",
                key="procedural_paths_not_relative")

        anatomy = instance.context.data["anatomy"]

        # Use project root variables for multiplatform support, see:
        # https://docs.arnoldrenderer.com/display/A5AFMUG/Search+Path
        # ':' as path separator is supported by Arnold for all platforms.
        keys = anatomy.root_environments().keys()
        paths = []
        for k in keys:
            paths.append("[{}]".format(k))

        self.log.info("discovered roots: {}".format(":".join(paths)))

        if ":".join(paths) not in texture_search_path:
            raise PublishXmlValidationError(
                self, "Project roots are not in textures search path.",
                key="project_not_in_texture")

        if ":".join(paths) not in procedural_search_path:
            raise PublishXmlValidationError(
                self, "Project roots are not in procedural search path.",
                key="project_not_in_procedural")

    @classmethod
    def repair(cls, instance):
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
        if isinstance(attr_val, types.BooleanType):
            return attr_val
        elif isinstance(attr_val, (types.ListType, types.GeneratorType)):
            return any(attr_val)
        else:
            return bool(attr_val)
