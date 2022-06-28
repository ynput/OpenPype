# -*- coding: utf-8 -*-
"""Create instance of vrayscene."""
import os
import json
import appdirs
import requests

from maya import cmds
import maya.app.renderSetup.model.renderSetup as renderSetup

from openpype.hosts.maya.api import (
    lib,
    plugin
)
from openpype.api import (
    get_system_settings,
    get_project_settings
)

from openpype.lib import requests_get
from openpype.pipeline import (
    CreatorError,
    legacy_io,
)
from openpype.modules import ModulesManager


class CreateVRayScene(plugin.Creator):
    """Create Vray Scene."""

    label = "VRay Scene"
    family = "vrayscene"
    icon = "cubes"

    _project_settings = None

    def __init__(self, *args, **kwargs):
        """Entry."""
        super(CreateVRayScene, self).__init__(*args, **kwargs)
        self._rs = renderSetup.instance()
        self.data["exportOnFarm"] = False
        deadline_settings = get_system_settings()["modules"]["deadline"]

        manager = ModulesManager()
        self.deadline_module = manager.modules_by_name["deadline"]

        if not deadline_settings["enabled"]:
            self.deadline_servers = {}
            return
        self._project_settings = get_project_settings(
            legacy_io.Session["AVALON_PROJECT"])

        try:
            default_servers = deadline_settings["deadline_urls"]
            project_servers = (
                self._project_settings["deadline"]["deadline_servers"]
            )
            self.deadline_servers = {
                k: default_servers[k]
                for k in project_servers
                if k in default_servers
            }

            if not self.deadline_servers:
                self.deadline_servers = default_servers

        except AttributeError:
            # Handle situation were we had only one url for deadline.
            # get default deadline webservice url from deadline module
            self.deadline_servers = self.deadline_module.deadline_urls

    def process(self):
        """Entry point."""
        exists = cmds.ls(self.name)
        if exists:
            return cmds.warning("%s already exists." % exists[0])

        use_selection = self.options.get("useSelection")
        with lib.undo_chunk():
            self._create_vray_instance_settings()
            self.instance = super(CreateVRayScene, self).process()

            index = 1
            namespace_name = "_{}".format(str(self.instance))
            try:
                cmds.namespace(rm=namespace_name)
            except RuntimeError:
                # namespace is not empty, so we leave it untouched
                pass

            while(cmds.namespace(exists=namespace_name)):
                namespace_name = "_{}{}".format(str(self.instance), index)
                index += 1

            namespace = cmds.namespace(add=namespace_name)

            # add Deadline server selection list
            if self.deadline_servers:
                cmds.scriptJob(
                    attributeChange=[
                        "{}.deadlineServers".format(self.instance),
                        self._deadline_webservice_changed
                    ])

            # create namespace with instance
            layers = self._rs.getRenderLayers()
            if use_selection:
                print(">>> processing existing layers")
                sets = []
                for layer in layers:
                    print("  - creating set for {}".format(layer.name()))
                    render_set = cmds.sets(
                        n="{}:{}".format(namespace, layer.name()))
                    sets.append(render_set)
                cmds.sets(sets, forceElement=self.instance)

            # if no render layers are present, create default one with
            # asterix selector
            if not layers:
                render_layer = self._rs.createRenderLayer('Main')
                collection = render_layer.createCollection("defaultCollection")
                collection.getSelector().setPattern('*')

    def _deadline_webservice_changed(self):
        """Refresh Deadline server dependent options."""
        # get selected server
        from maya import cmds
        webservice = self.deadline_servers[
            self.server_aliases[
                cmds.getAttr("{}.deadlineServers".format(self.instance))
            ]
        ]
        pools = self.deadline_module.get_deadline_pools(webservice)
        cmds.deleteAttr("{}.primaryPool".format(self.instance))
        cmds.deleteAttr("{}.secondaryPool".format(self.instance))
        cmds.addAttr(self.instance, longName="primaryPool",
                     attributeType="enum",
                     enumName=":".join(pools))
        cmds.addAttr(self.instance, longName="secondaryPool",
                     attributeType="enum",
                     enumName=":".join(["-"] + pools))

    def _create_vray_instance_settings(self):
        # get pools
        pools = []

        system_settings = get_system_settings()["modules"]

        deadline_enabled = system_settings["deadline"]["enabled"]
        muster_enabled = system_settings["muster"]["enabled"]
        muster_url = system_settings["muster"]["MUSTER_REST_URL"]

        if deadline_enabled and muster_enabled:
            self.log.error(
                "Both Deadline and Muster are enabled. " "Cannot support both."
            )
            raise CreatorError("Both Deadline and Muster are enabled")

        self.server_aliases = self.deadline_servers.keys()
        self.data["deadlineServers"] = self.server_aliases

        if deadline_enabled:
            # if default server is not between selected, use first one for
            # initial list of pools.
            try:
                deadline_url = self.deadline_servers["default"]
            except KeyError:
                deadline_url = [
                    self.deadline_servers[k]
                    for k in self.deadline_servers.keys()
                ][0]

            pool_names = self.deadline_module.get_deadline_pools(deadline_url)

        if muster_enabled:
            self.log.info(">>> Loading Muster credentials ...")
            self._load_credentials()
            self.log.info(">>> Getting pools ...")
            try:
                pools = self._get_muster_pools()
            except requests.exceptions.HTTPError as e:
                if e.startswith("401"):
                    self.log.warning("access token expired")
                    self._show_login()
                    raise CreatorError("Access token expired")
            except requests.exceptions.ConnectionError:
                self.log.error("Cannot connect to Muster API endpoint.")
                raise CreatorError("Cannot connect to {}".format(muster_url))
            pool_names = []
            for pool in pools:
                self.log.info("  - pool: {}".format(pool["name"]))
                pool_names.append(pool["name"])

            self.data["primaryPool"] = pool_names

        self.data["suspendPublishJob"] = False
        self.data["priority"] = 50
        self.data["whitelist"] = False
        self.data["machineList"] = ""
        self.data["vraySceneMultipleFiles"] = False
        self.options = {"useSelection": False}  # Force no content

    def _load_credentials(self):
        """Load Muster credentials.

        Load Muster credentials from file and set ``MUSTER_USER``,
        ``MUSTER_PASSWORD``, ``MUSTER_REST_URL`` is loaded from presets.

        Raises:
            CreatorError: If loaded credentials are invalid.
            AttributeError: If ``MUSTER_REST_URL`` is not set.

        """
        app_dir = os.path.normpath(appdirs.user_data_dir("pype-app", "pype"))
        file_name = "muster_cred.json"
        fpath = os.path.join(app_dir, file_name)
        file = open(fpath, "r")
        muster_json = json.load(file)
        self._token = muster_json.get("token", None)
        if not self._token:
            self._show_login()
            raise CreatorError("Invalid access token for Muster")
        file.close()
        self.MUSTER_REST_URL = os.environ.get("MUSTER_REST_URL")
        if not self.MUSTER_REST_URL:
            raise AttributeError("Muster REST API url not set")

    def _get_muster_pools(self):
        """Get render pools from Muster.

        Raises:
            CreatorError: If pool list cannot be obtained from Muster.

        """
        params = {"authToken": self._token}
        api_entry = "/api/pools/list"
        response = requests_get(self.MUSTER_REST_URL + api_entry,
                                params=params)
        if response.status_code != 200:
            if response.status_code == 401:
                self.log.warning("Authentication token expired.")
                self._show_login()
            else:
                self.log.error(
                    ("Cannot get pools from "
                     "Muster: {}").format(response.status_code)
                )
                raise CreatorError("Cannot get pools from Muster")
        try:
            pools = response.json()["ResponseData"]["pools"]
        except ValueError as e:
            self.log.error("Invalid response from Muster server {}".format(e))
            raise CreatorError("Invalid response from Muster server")

        return pools

    def _show_login(self):
        # authentication token expired so we need to login to Muster
        # again to get it. We use Pype API call to show login window.
        api_url = "{}/muster/show_login".format(
            os.environ["OPENPYPE_WEBSERVER_URL"])
        self.log.debug(api_url)
        login_response = requests_get(api_url, timeout=1)
        if login_response.status_code != 200:
            self.log.error("Cannot show login form to Muster")
            raise CreatorError("Cannot show login form to Muster")
