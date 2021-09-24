#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import pwd
import grp
import os
import sys
import subprocess
import json
from copy import deepcopy

flame_python_path = "/opt/Autodesk/flame_2021/python"
flame_exe_path = "/opt/Autodesk/flame_2021/bin/flame.app/Contents/MacOS/startApp"

sys.path.append(flame_python_path)

from libwiretapPythonClientAPI import (
    WireTapClientInit,
    WireTapClientUninit,
    WireTapNodeHandle,
    WireTapServerHandle,
    WireTapInt,
    WireTapStr,
)

class WireTapCom(object):
    """
    Comunicator class wrapper for talking to WireTap
    """

    def __init__(self, host_name=None, volume_name=None, group_name=None):

        WireTapClientInit()

        self.host_name = host_name or "localhost"
        self.volume_name = volume_name or "stonefs"
        self.group_name = group_name or "staff"

        self._server = WireTapServerHandle("{}:IFFFS".format(self.host_name))
        print("WireTap connected at '{}'...".format(
            self.host_name))

    def close(self):
        self._server = None
        WireTapClientUninit()
        print("WireTap closed...")

    def get_launch_args(self,
            project_name, user_name, workspace_name=None, *args, **kwargs):

        self._project_prep(project_name, user_name, workspace_name)
        self._user_prep(user_name)

        if workspace_name is None:
            # default workspace
            print("Using a default workspace")
            return (
                "--start-project='{}' --start-user='{}' --create-workspace"
            ).format(
                project_name,
                user_name,
            )

        else:
            print(
                "Using a custom workspace '{}'".format(workspace_name))

            self._workspace_prep(project_name, workspace_name)
            return (
                "--start-project='{}' --start-user='{}' "
                "--create-workspace --start-workspace='{}'").format(
                    project_name, user_name, workspace_name)


    def _user_prep(self, user_name):
        """Ensuring user does exists in user's stack

        Args:
            user_name (str): name of a user

        Raises:
            AttributeError: unable to create user
        """

        if not self._child_is_in_parent_path("/users", user_name, "USER"):
            # Create the new user
            users = WireTapNodeHandle(self._server, "/users")
            print(">> dir users: {}".format(dir(users)))
            print(">> users obj: {}".format(users))

            # todo: check what users are available in stack and find lastly
            #       created which is matching at least partly to the
            #       input user_name

            user_node = WireTapNodeHandle()
            if not users.createNode(user_name, "USER", user_node):
                raise AttributeError(
                    "User {} cannot be created: {}".format(
                        user_name, users.lastError())
                )

            print("User `{}` is created".format(user_name))

    def _workspace_prep(self, project_name, workspace_name):
        """Preparing a workspace

        In case it doesn not exists it will create one

        Args:
            project_name (str): project name
            workspace_name (str): workspace name

        Raises:
            AttributeError: unable to create workspace
        """
        workspace_exists = self._child_is_in_parent_path(
            "/projects/{}".format(project_name), workspace_name, "WORKSPACE"
        )
        if not workspace_exists:
            project = WireTapNodeHandle(
                self._server, "/projects/{}".format(project_name))

            workspace_node = WireTapNodeHandle()
            created_workspace = project.createNode(
                workspace_name, "WORKSPACE", workspace_node)

            if not created_workspace:
                raise AttributeError(
                    "Cannot create workspace `{}` in "
                    "project `{}`: `{}`".format(
                        workspace_name, project_name, project.lastError())
                )

        print(
            "Workspace `{}` is successfully created".format(workspace_name))

    def _project_prep(self, project_name, user_name, workspace_name):

        project_exists = self._child_is_in_parent_path(
            "/projects", project_name, "PROJECT")

        if not project_exists:

            volumes = self._get_volumes()

            if len(volumes) == 0:
                raise AttributeError(
                    "Cannot create new project! There are no volumes defined for this Flame!"
                )


            # sanity check :)
            if self.volume_name not in volumes:
                raise AttributeError(
                    "Volume '%s' specified in hook does not exist in "
                    "list of current volumes '%s'" % (
                        self.volume_name, volumes)
                )

            project_create_cmd = [\
                os.path.join(
                    "/opt/Autodesk/",
                    "wiretap",
                    "tools",
                    "2021",
                    "wiretap_create_node",
                ),
                '-n',
                os.path.join("/volumes", self.volume_name),
                '-d',
                project_name,
                '-g',
            ]

            project_create_cmd.append(self.group_name)

            print(project_create_cmd)

            exit_code = subprocess.call(
                project_create_cmd,
                cwd=os.path.expanduser('~'))

            if exit_code != 0:
                RuntimeError("Cannot create project in flame db")

            # create project settings
            print(
                "A new project '%s' will be created." % project_name)


    def _get_volumes(self):

        root = WireTapNodeHandle(self._server, "/volumes")
        num_children = WireTapInt(0)

        get_children_num = root.getNumChildren(num_children)
        if not get_children_num:
            raise AttributeError(
                "Cannot get number of volumes: {}".format(root.lastError())
            )

        volumes = []

        # go trough all children and get volume names
        child_obj = WireTapNodeHandle()
        for child_idx in range(num_children):

            # get a child
            if not root.getChild(child_idx, child_obj):
                raise AttributeError(
                    "Unable to get child: {}".format(root.lastError()))

            node_name = WireTapStr()
            get_children_name = child_obj.getDisplayName(node_name)

            if not get_children_name:
                raise AttributeError(
                    "Unable to get child name: {}".format(child_obj.lastError())
                )

            volumes.append(node_name.c_str())

        return volumes

    def _get_groups(self):

        # fetch all group which the user is a part of
        user = pwd.getpwuid(os.geteuid()).pw_name  # current user
        groups = [
            g.gr_name for g in grp.getgrall() if user in g.gr_mem
        ]  # compare user name with group database
        gid = pwd.getpwnam(
            user
        ).pw_gid  # make sure current group is added if database if incomplete
        default_group = grp.getgrgid(gid).gr_name
        if default_group not in groups:
            groups.append(default_group)

        return (default_group, groups)

    def _child_is_in_parent_path(self, parent_path, child_name, child_type):
        # get the parent
        parent = WireTapNodeHandle(self._server, parent_path)

        # get number of children
        num_children = WireTapInt(0)
        if not parent.getNumChildren(num_children):
            raise AttributeError(
                "Wiretap Error: Unable to obtain number of "
                "children for node %s. Please check that your "
                "wiretap service is running. "
                "Error reported: %s" % (parent_path, parent.lastError())
            )

        # iterate over children, look for the given node
        child_obj = WireTapNodeHandle()
        for child_idx in range(num_children):

            # get the child
            if not parent.getChild(child_idx, child_obj):
                raise AttributeError(
                    "Unable to get child: {}".format(
                        parent.lastError()))

            node_name = WireTapStr()
            node_type = WireTapStr()

            if not child_obj.getDisplayName(node_name):
                raise AttributeError(
                    "Unable to get child name: %s" % child_obj.lastError()
                )
            if not child_obj.getNodeTypeStr(node_type):
                raise AttributeError(
                    "Unable to obtain child type: %s" % child_obj.lastError()
                )

            if (node_name.c_str() == child_name) and (
                    node_type.c_str() == child_type):
                return True

        return False


if __name__ == "__main__":
    json_path = sys.argv[-1]
    in_data = json.loads(json_path)
    out_data = deepcopy(in_data)

    wiretap_handler = WireTapCom()

    try:
        app_args = wiretap_handler.get_launch_args(
            project_name=in_data["project_data"],
            user_name=in_data["user_name"],
            workspace_name=in_data.get("workspace_mame")
        )
    finally:
        wiretap_handler.close()

    out_data.update({
        "app_args": app_args
    })

    with open(json_path, "w") as file_stream:
        json.dump(out_data, file_stream, indent=4)
