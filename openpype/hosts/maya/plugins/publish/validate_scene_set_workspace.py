import os

import maya.cmds as cmds
import pyblish.api

from openpype.pipeline.publish import (
    PublishValidationError, ValidatePipelineOrder)


def is_subdir(path, root_dir):
    """ Returns whether path is a subdirectory (or file) within root_dir """
    path = os.path.realpath(path)
    root_dir = os.path.realpath(root_dir)

    # If not on same drive
    if os.path.splitdrive(path)[0].lower() != os.path.splitdrive(root_dir)[0].lower():  # noqa: E501
        return False

    # Get 'relative path' (can contain ../ which means going up)
    relative = os.path.relpath(path, root_dir)

    # Check if the path starts by going up, if so it's not a subdirectory. :)
    if relative.startswith(os.pardir) or relative == os.curdir:
        return False
    else:
        return True


class ValidateSceneSetWorkspace(pyblish.api.ContextPlugin):
    """Validate the scene is inside the currently set Maya workspace"""

    order = ValidatePipelineOrder
    hosts = ['maya']
    label = 'Maya Workspace Set'

    def process(self, context):

        scene_name = cmds.file(query=True, sceneName=True)
        if not scene_name:
            raise PublishValidationError(
                "Scene hasn't been saved. Workspace can't be validated.")

        root_dir = cmds.workspace(query=True, rootDirectory=True)

        if not is_subdir(scene_name, root_dir):
            raise PublishValidationError(
                "Maya workspace is not set correctly.\n\n"
                f"Current workfile `{scene_name}` is not inside the "
                "current Maya project root directory `{root_dir}`.\n\n"
                "Please use Workfile app to re-save."
            )
