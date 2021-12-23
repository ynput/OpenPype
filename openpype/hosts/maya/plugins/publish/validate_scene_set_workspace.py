import os

import maya.cmds as cmds

import pyblish.api
import openpype.api
from openpype.lib.profiles_filtering import filter_profiles


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


class ValidateSceneSetWorkspace(pyblish.api.InstancePlugin):
    """Validate the scene is inside the currently set Maya workspace"""

    order = openpype.api.ValidatePipelineOrder
    hosts = ['maya']
    category = 'scene'
    version = (0, 1, 0)
    label = 'Maya Workspace Set'

    publish_from_published_workfiles = False

    def process(self, instance):

        context = instance.context
        scene_name = cmds.file(query=True, sceneName=True)
        if not scene_name:
            raise RuntimeError("Scene hasn't been saved. Workspace can't be "
                               "validated.")

        root_dir = cmds.workspace(query=True, rootDirectory=True)

        if not is_subdir(scene_name, root_dir):

            if not self.publish_from_published_workfiles:
                raise RuntimeError("Maya workspace is not set correctly.")
            else:
                settings = context.data.get('project_settings')
                template_name_profiles = settings.get('global') \
                    .get('publish') \
                    .get('IntegrateAssetNew') \
                    .get('template_name_profiles')
                task_name = context.data["anatomyData"]["task"]["name"]
                task_type = context.data["anatomyData"]["task"]["type"]
                key_values = {
                    "families": "workfile",
                    "tasks": task_name,
                    "hosts": context.data["hostName"],
                    "task_types": task_type
                }
                profile = filter_profiles(
                    template_name_profiles,
                    key_values,
                    logger=self.log
                )
                anatomy = context.data.get('anatomy')
                anatomy_filled = anatomy.format(
                    instance.data.get('anatomyData')
                )
                pub_workfile_path = anatomy_filled.get(
                    profile["template_name"]
                ).get("folder")

                if not is_subdir(scene_name, pub_workfile_path):
                    raise RuntimeError("Maya workspace is not set correctly.")
