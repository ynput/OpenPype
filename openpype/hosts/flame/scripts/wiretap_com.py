#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import pwd
import grp
import os
import sys
import subprocess
import json
import xml.dom.minidom as minidom
from copy import deepcopy
import datetime

flame_python_path = "/opt/Autodesk/flame_2021/python"
flame_exe_path = "/opt/Autodesk/flame_2021/bin/flame.app/Contents/MacOS/startApp"

sys.path.append(flame_python_path)

from libwiretapPythonClientAPI import (
    WireTapClientInit,
    WireTapClientUninit,
    WireTapNodeHandle,
    WireTapServerHandle,
    WireTapInt,
    WireTapStr
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

    def get_launch_args(
        self, project_name, project_data, user_name, workspace_name=None,
            *args, **kwargs):

        self._project_prep(project_name)
        self._set_project_settings(project_name, project_data)
        user_name = self._user_prep(user_name)

        if workspace_name is None:
            # default workspace
            print("Using a default workspace")
            return [
                "--start-project={}".format(project_name),
                "--start-user={}".format(user_name),
                "--create-workspace"
            ]

        else:
            print(
                "Using a custom workspace '{}'".format(workspace_name))

            self._workspace_prep(project_name, workspace_name)
            return [
                "--start-project={}".format(project_name),
                "--start-user={}".format(user_name),
                "--create-workspace",
                "--start-workspace={}".format(workspace_name)
            ]

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

    def _project_prep(self, project_name):

        project_exists = self._child_is_in_parent_path(
            "/projects", project_name, "PROJECT")

        if not project_exists:

            volumes = self._get_all_volumes()

            if len(volumes) == 0:
                raise AttributeError(
                    "Not able to create new project. No Volumes existing"
                )

            # check if volumes exists
            if self.volume_name not in volumes:
                raise AttributeError(
                    ("Volume '{}' does not exist '{}'").format(
                        self.volume_name, volumes)
                )

            project_create_cmd = [
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

            print(
                "A new project '{}' is created.".format(project_name))

    def _get_all_volumes(self):

        root = WireTapNodeHandle(self._server, "/volumes")
        children_num = WireTapInt(0)

        get_children_num = root.getNumChildren(children_num)
        if not get_children_num:
            raise AttributeError(
                "Cannot get number of volumes: {}".format(root.lastError())
            )

        volumes = []

        # go trough all children and get volume names
        child_obj = WireTapNodeHandle()
        for child_idx in range(children_num):

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

    def _user_prep(self, user_name):
        """Ensuring user does exists in user's stack

        Args:
            user_name (str): name of a user

        Raises:
            AttributeError: unable to create user
        """

        # get all used usernames in db
        used_names = self._get_usernames()
        print(">> used_names: {}".format(used_names))

        # filter only those which are sharing input user name
        filtered_users = [user for user in used_names if user_name in user]

        if filtered_users:
            # todo: need to find lastly created following regex patern for date used in name
            return filtered_users.pop()

        # create new user name with date in suffix
        now = datetime.datetime.now() # current date and time
        date = now.strftime("%Y%m%d")
        new_user_name = "{}_{}".format(user_name, date)
        print(new_user_name)

        if not self._child_is_in_parent_path("/users", new_user_name, "USER"):
            # Create the new user
            users = WireTapNodeHandle(self._server, "/users")

            user_node = WireTapNodeHandle()
            created_user = users.createNode(new_user_name, "USER", user_node)
            if not created_user:
                raise AttributeError(
                    "User {} cannot be created: {}".format(
                        new_user_name, users.lastError())
                )

            print("User `{}` is created".format(new_user_name))
            return new_user_name


    def _get_usernames(self):

        root = WireTapNodeHandle(self._server, "/users")
        children_num = WireTapInt(0)

        get_children_num = root.getNumChildren(children_num)
        if not get_children_num:
            raise AttributeError(
                "Cannot get number of volumes: {}".format(root.lastError())
            )

        usernames = []

        # go trough all children and get volume names
        child_obj = WireTapNodeHandle()
        for child_idx in range(children_num):

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

            usernames.append(node_name.c_str())

        return usernames

    def _child_is_in_parent_path(self, parent_path, child_name, child_type):
        parent = WireTapNodeHandle(self._server, parent_path)

        # iterate number of children
        children_num = WireTapInt(0)
        requested = parent.getNumChildren(children_num)
        if not requested:
            raise AttributeError((
                "Error: Cannot request number of "
                "childrens from the node {}. Make sure your "
                "wiretap service is running: {}").format(
                    parent_path, parent.lastError())
            )

        # iterate children
        child_obj = WireTapNodeHandle()
        for child_idx in range(children_num):
            if not parent.getChild(child_idx, child_obj):
                raise AttributeError(
                    "Cannot get child: {}".format(
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

    def _set_project_settings(self, project_name, project_data):

        # generated xml from project_data dict
        _xml = "<Project>"
        for key, value in project_data.items():
            _xml += "<{}>{}</{}>".format(key, value, key)
        _xml += "</Project>"

        pretty_xml = minidom.parseString(_xml).toprettyxml()
        print("__ xml: {}".format(pretty_xml))
        
        # set project data to wiretap
        project_node = WireTapNodeHandle(
            self._server, "/projects/{}".format(project_name))
        
        if not project_node.setMetaData("XML", _xml):
            raise AttributeError(
                "Not able to set metadata {}. Error: {}".format(
                    project_name, project_node.lastError())
            )

        print("Project settings successfully set.")


if __name__ == "__main__":
    json_path = sys.argv[-1]
    json_data = open(json_path).read()
    in_data = json.loads(json_data)
    out_data = deepcopy(in_data)

    wiretap_handler = WireTapCom()

    try:
        app_args = wiretap_handler.get_launch_args(
            project_name=in_data["project_name"],
            project_data=in_data["project_data"],
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
