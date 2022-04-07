#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import os
import sys
import subprocess
import json
import xml.dom.minidom as minidom
from copy import deepcopy
import datetime
from libwiretapPythonClientAPI import (  # noqa
    WireTapClientInit,
    WireTapClientUninit,
    WireTapNodeHandle,
    WireTapServerHandle,
    WireTapInt,
    WireTapStr
)


class WireTapCom(object):
    """
    Comunicator class wrapper for talking to WireTap db.

    This way we are able to set new project with settings and
    correct colorspace policy. Also we are able to create new user
    or get actual user with similar name (users are usually cloning
    their profiles and adding date stamp into suffix).
    """

    def __init__(self, host_name=None, volume_name=None, group_name=None):
        """Initialisation of WireTap communication class

        Args:
            host_name (str, optional): Name of host server. Defaults to None.
            volume_name (str, optional): Name of volume. Defaults to None.
            group_name (str, optional): Name of user group. Defaults to None.
        """
        # set main attributes of server
        # if there are none set the default installation
        self.host_name = host_name or "localhost"
        self.volume_name = volume_name or "stonefs"
        self.group_name = group_name or "staff"

        # wiretap tools dir path
        self.wiretap_tools_dir = os.getenv("OPENPYPE_WIRETAP_TOOLS")

        # initialize WireTap client
        WireTapClientInit()

        # add the server to shared variable
        self._server = WireTapServerHandle("{}:IFFFS".format(self.host_name))
        print("WireTap connected at '{}'...".format(
            self.host_name))

    def close(self):
        self._server = None
        WireTapClientUninit()
        print("WireTap closed...")

    def get_launch_args(
            self, project_name, project_data, user_name, *args, **kwargs):
        """Forming launch arguments for OpenPype launcher.

        Args:
            project_name (str): name of project
            project_data (dict): Flame compatible project data
            user_name (str): name of user

        Returns:
            list: arguments
        """

        workspace_name = kwargs.get("workspace_name")
        color_policy = kwargs.get("color_policy")

        project_exists = self._project_prep(project_name)
        if not project_exists:
            self._set_project_settings(project_name, project_data)
            self._set_project_colorspace(project_name, color_policy)

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
        """Preparing a project

        In case it doesn not exists it will create one

        Args:
            project_name (str): project name

        Raises:
            AttributeError: unable to create project
        """
        # test if projeft exists
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
                    ("Volume '{}' does not exist in '{}'").format(
                        self.volume_name, volumes)
                )

            # form cmd arguments
            project_create_cmd = [
                os.path.join(
                    self.wiretap_tools_dir,
                    "wiretap_create_node"
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
                cwd=os.path.expanduser('~'),
                preexec_fn=_subprocess_preexec_fn
            )

            if exit_code != 0:
                RuntimeError("Cannot create project in flame db")

            print(
                "A new project '{}' is created.".format(project_name))
        return project_exists

    def _get_all_volumes(self):
        """Request all available volumens from WireTap

        Returns:
            list: all available volumes in server

        Rises:
            AttributeError: unable to get any volumes childs from server
        """
        root = WireTapNodeHandle(self._server, "/volumes")
        children_num = WireTapInt(0)

        get_children_num = root.getNumChildren(children_num)
        if not get_children_num:
            raise AttributeError(
                "Cannot get number of volumes: {}".format(root.lastError())
            )

        volumes = []

        # go through all children and get volume names
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
                    "Unable to get child name: {}".format(
                        child_obj.lastError())
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
            # TODO: need to find lastly created following regex pattern for
            # date used in name
            return filtered_users.pop()

        # create new user name with date in suffix
        now = datetime.datetime.now()  # current date and time
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
        """Requesting all available users from WireTap

        Returns:
            list: all available user names

        Raises:
            AttributeError: there are no users in server
        """
        root = WireTapNodeHandle(self._server, "/users")
        children_num = WireTapInt(0)

        get_children_num = root.getNumChildren(children_num)
        if not get_children_num:
            raise AttributeError(
                "Cannot get number of volumes: {}".format(root.lastError())
            )

        usernames = []

        # go through all children and get volume names
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
                    "Unable to get child name: {}".format(
                        child_obj.lastError())
                )

            usernames.append(node_name.c_str())

        return usernames

    def _child_is_in_parent_path(self, parent_path, child_name, child_type):
        """Checking if a given child is in parent path.

        Args:
            parent_path (str): db path to parent
            child_name (str): name of child
            child_type (str): type of child

        Raises:
            AttributeError: Not able to get number of children
            AttributeError: Not able to get children form parent
            AttributeError: Not able to get children name
            AttributeError: Not able to get children type

        Returns:
            bool: True if child is in parent path
        """
        parent = WireTapNodeHandle(self._server, parent_path)

        # iterate number of children
        children_num = WireTapInt(0)
        requested = parent.getNumChildren(children_num)
        if not requested:
            raise AttributeError((
                "Error: Cannot request number of "
                "children from the node {}. Make sure your "
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
        """Setting project attributes.

        Args:
            project_name (str): name of project
            project_data (dict): data with project attributes
                                 (flame compatible)

        Raises:
            AttributeError: Not able to set project attributes
        """
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
                "Not able to set project attributes {}. Error: {}".format(
                    project_name, project_node.lastError())
            )

        print("Project settings successfully set.")

    def _set_project_colorspace(self, project_name, color_policy):
        """Set project's colorspace policy.

        Args:
            project_name (str): name of project
            color_policy (str): name of policy

        Raises:
            RuntimeError: Not able to set colorspace policy
        """
        color_policy = color_policy or "Legacy"

        # check if the colour policy in custom dir
        if "/" in color_policy:
            # if unlikelly full path was used make it redundant
            color_policy = color_policy.replace("/syncolor/policies/", "")
            # expecting input is `Shared/NameOfPolicy`
            color_policy = "/syncolor/policies/{}".format(
                color_policy)
        else:
            color_policy = "/syncolor/policies/Autodesk/{}".format(
                color_policy)

        # create arguments
        project_colorspace_cmd = [
            os.path.join(
                self.wiretap_tools_dir,
                "wiretap_duplicate_node"
            ),
            "-s",
            color_policy,
            "-n",
            "/projects/{}/syncolor".format(project_name)
        ]

        print(project_colorspace_cmd)

        exit_code = subprocess.call(
            project_colorspace_cmd,
            cwd=os.path.expanduser('~'),
            preexec_fn=_subprocess_preexec_fn
        )

        if exit_code != 0:
            RuntimeError("Cannot set colorspace {} on project {}".format(
                color_policy, project_name
            ))


def _subprocess_preexec_fn():
    os.setpgrp()
    os.umask(0o000)


if __name__ == "__main__":
    # get json exchange data
    json_path = sys.argv[-1]
    json_data = open(json_path).read()
    in_data = json.loads(json_data)
    out_data = deepcopy(in_data)

    # get main server attributes
    host_name = in_data.pop("host_name")
    volume_name = in_data.pop("volume_name")
    group_name = in_data.pop("group_name")

    # initialize class
    wiretap_handler = WireTapCom(host_name, volume_name, group_name)

    try:
        app_args = wiretap_handler.get_launch_args(
            project_name=in_data.pop("project_name"),
            project_data=in_data.pop("project_data"),
            user_name=in_data.pop("user_name"),
            **in_data
        )
    finally:
        wiretap_handler.close()

    # set returned args back to out data
    out_data.update({
        "app_args": app_args
    })

    # write it out back to the exchange json file
    with open(json_path, "w") as file_stream:
        json.dump(out_data, file_stream, indent=4)
