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
from openpype.api import get_system_settings


class CreateVRayScene(plugin.Creator):
    """Create Vray Scene."""

    label = "VRay Scene"
    family = "vrayscene"
    icon = "cubes"

    def __init__(self, *args, **kwargs):
        """Entry."""
        super(CreateVRayScene, self).__init__(*args, **kwargs)
        self._rs = renderSetup.instance()
        self.data["exportOnFarm"] = False

    def process(self):
        """Entry point."""
        exists = cmds.ls(self.name)
        if exists:
            return cmds.warning("%s already exists." % exists[0])

        use_selection = self.options.get("useSelection")
        with lib.undo_chunk():
            self._create_vray_instance_settings()
            instance = super(CreateVRayScene, self).process()

            index = 1
            namespace_name = "_{}".format(str(instance))
            try:
                cmds.namespace(rm=namespace_name)
            except RuntimeError:
                # namespace is not empty, so we leave it untouched
                pass

            while(cmds.namespace(exists=namespace_name)):
                namespace_name = "_{}{}".format(str(instance), index)
                index += 1

            namespace = cmds.namespace(add=namespace_name)
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
                cmds.sets(sets, forceElement=instance)

            # if no render layers are present, create default one with
            # asterix selector
            if not layers:
                render_layer = self._rs.createRenderLayer('Main')
                collection = render_layer.createCollection("defaultCollection")
                collection.getSelector().setPattern('*')

    def _create_vray_instance_settings(self):
        # get pools
        pools = []

        system_settings = get_system_settings()["modules"]

        deadline_enabled = system_settings["deadline"]["enabled"]
        muster_enabled = system_settings["muster"]["enabled"]
        deadline_url = system_settings["deadline"]["DEADLINE_REST_URL"]
        muster_url = system_settings["muster"]["MUSTER_REST_URL"]

        if deadline_enabled and muster_enabled:
            self.log.error(
                "Both Deadline and Muster are enabled. " "Cannot support both."
            )
            raise RuntimeError("Both Deadline and Muster are enabled")

        if deadline_enabled:
            argument = "{}/api/pools?NamesOnly=true".format(deadline_url)
            try:
                response = self._requests_get(argument)
            except requests.exceptions.ConnectionError as e:
                msg = 'Cannot connect to deadline web service'
                self.log.error(msg)
                raise RuntimeError('{} - {}'.format(msg, e))
            if not response.ok:
                self.log.warning("No pools retrieved")
            else:
                pools = response.json()
                self.data["primaryPool"] = pools
                # We add a string "-" to allow the user to not
                # set any secondary pools
                self.data["secondaryPool"] = ["-"] + pools

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
                    raise RuntimeError("Access token expired")
            except requests.exceptions.ConnectionError:
                self.log.error("Cannot connect to Muster API endpoint.")
                raise RuntimeError("Cannot connect to {}".format(muster_url))
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
            RuntimeError: If loaded credentials are invalid.
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
            raise RuntimeError("Invalid access token for Muster")
        file.close()
        self.MUSTER_REST_URL = os.environ.get("MUSTER_REST_URL")
        if not self.MUSTER_REST_URL:
            raise AttributeError("Muster REST API url not set")

    def _get_muster_pools(self):
        """Get render pools from Muster.

        Raises:
            Exception: If pool list cannot be obtained from Muster.

        """
        params = {"authToken": self._token}
        api_entry = "/api/pools/list"
        response = self._requests_get(self.MUSTER_REST_URL + api_entry,
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
                raise Exception("Cannot get pools from Muster")
        try:
            pools = response.json()["ResponseData"]["pools"]
        except ValueError as e:
            self.log.error("Invalid response from Muster server {}".format(e))
            raise Exception("Invalid response from Muster server")

        return pools

    def _show_login(self):
        # authentication token expired so we need to login to Muster
        # again to get it. We use Pype API call to show login window.
        api_url = "{}/muster/show_login".format(
            os.environ["OPENPYPE_WEBSERVER_URL"])
        self.log.debug(api_url)
        login_response = self._requests_get(api_url, timeout=1)
        if login_response.status_code != 200:
            self.log.error("Cannot show login form to Muster")
            raise Exception("Cannot show login form to Muster")

    def _requests_post(self, *args, **kwargs):
        """Wrap request post method.

        Disabling SSL certificate validation if ``DONT_VERIFY_SSL`` environment
        variable is found. This is useful when Deadline or Muster server are
        running with self-signed certificates and their certificate is not
        added to trusted certificates on client machines.

        Warning:
            Disabling SSL certificate validation is defeating one line
            of defense SSL is providing and it is not recommended.

        """
        if "verify" not in kwargs:
            kwargs["verify"] = (
                False if os.getenv("OPENPYPE_DONT_VERIFY_SSL", True) else True
            )  # noqa
        return requests.post(*args, **kwargs)

    def _requests_get(self, *args, **kwargs):
        """Wrap request get method.

        Disabling SSL certificate validation if ``DONT_VERIFY_SSL`` environment
        variable is found. This is useful when Deadline or Muster server are
        running with self-signed certificates and their certificate is not
        added to trusted certificates on client machines.

        Warning:
            Disabling SSL certificate validation is defeating one line
            of defense SSL is providing and it is not recommended.

        """
        if "verify" not in kwargs:
            kwargs["verify"] = (
                False if os.getenv("OPENPYPE_DONT_VERIFY_SSL", True) else True
            )  # noqa
        return requests.get(*args, **kwargs)
