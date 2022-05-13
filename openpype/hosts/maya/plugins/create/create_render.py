# -*- coding: utf-8 -*-
"""Create ``Render`` instance in Maya."""
import json
import os

import appdirs
import requests

from maya import cmds
from maya.app.renderSetup.model import renderSetup

from openpype.api import (
    get_system_settings,
    get_project_settings,
)
from openpype.hosts.maya.api import (
    lib,
    lib_rendersettings,
    plugin
)
from openpype.modules import ModulesManager
from openpype.pipeline import legacy_io


class CreateRender(plugin.Creator):
    """Create *render* instance.

    Render instances are not actually published, they hold options for
    collecting of render data. It render instance is present, it will trigger
    collection of render layers, AOVs, cameras for either direct submission
    to render farm or export as various standalone formats (like V-Rays
    ``vrscenes`` or Arnolds ``ass`` files) and then submitting them to render
    farm.

    Instance has following attributes::

        primaryPool (list of str): Primary list of slave machine pool to use.
        secondaryPool (list of str): Optional secondary list of slave pools.
        suspendPublishJob (bool): Suspend the job after it is submitted.
        extendFrames (bool): Use already existing frames from previous version
            to extend current render.
        overrideExistingFrame (bool): Overwrite already existing frames.
        priority (int): Submitted job priority
        framesPerTask (int): How many frames per task to render. This is
            basically job division on render farm.
        whitelist (list of str): White list of slave machines
        machineList (list of str): Specific list of slave machines to use
        useMayaBatch (bool): Use Maya batch mode to render as opposite to
            Maya interactive mode. This consumes different licenses.
        vrscene (bool): Submit as ``vrscene`` file for standalone V-Ray
            renderer.
        ass (bool): Submit as ``ass`` file for standalone Arnold renderer.
        tileRendering (bool): Instance is set to tile rendering mode. We
            won't submit actual render, but we'll make publish job to wait
            for Tile Assembly job done and then publish.

    See Also:
        https://pype.club/docs/artist_hosts_maya#creating-basic-render-setup

    """

    label = "Render"
    family = "rendering"
    icon = "eye"

    _token = None
    _user = None
    _password = None

    _project_settings = None

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super(CreateRender, self).__init__(*args, **kwargs)
        deadline_settings = get_system_settings()["modules"]["deadline"]
        if not deadline_settings["enabled"]:
            self.deadline_servers = {}
            return
        self._project_settings = get_project_settings(
            legacy_io.Session["AVALON_PROJECT"])

        manager = ModulesManager()
        self.deadline_module = manager.modules_by_name["deadline"]
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
            cmds.warning("%s already exists." % exists[0])
            return

        use_selection = self.options.get("useSelection")
        with lib.undo_chunk():
            self._create_render_settings()
            self.instance = super(CreateRender, self).process()
            # create namespace with instance
            index = 1
            namespace_name = "_{}".format(str(self.instance))
            try:
                cmds.namespace(rm=namespace_name)
            except RuntimeError:
                # namespace is not empty, so we leave it untouched
                pass

            while cmds.namespace(exists=namespace_name):
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

            cmds.setAttr("{}.machineList".format(self.instance), lock=True)
            rs = renderSetup.instance()
            layers = rs.getRenderLayers()
            if use_selection:
                self.log.info("Processing existing layers")
                sets = []
                for layer in layers:
                    self.log.info("  - creating set for {}:{}".format(
                        namespace, layer.name()))
                    render_set = cmds.sets(
                        n="{}:{}".format(namespace, layer.name()))
                    sets.append(render_set)
                cmds.sets(sets, forceElement=self.instance)

            # if no render layers are present, create default one with
            # asterisk selector
            if not layers:
                render_layer = rs.createRenderLayer('Main')
                collection = render_layer.createCollection("defaultCollection")
                collection.getSelector().setPattern('*')

            self.log.info("Applying default render settings..")
            lib_rendersettings.RenderSettings.apply_defaults()
        return self.instance

    def _deadline_webservice_changed(self):
        """Refresh Deadline server dependent options."""
        # get selected server
        webservice = self.deadline_servers[
            self.server_aliases[
                cmds.getAttr("{}.deadlineServers".format(self.instance))
            ]
        ]
        pools = self.deadline_module.get_deadline_pools(webservice, self.log)
        cmds.deleteAttr("{}.primaryPool".format(self.instance))
        cmds.deleteAttr("{}.secondaryPool".format(self.instance))

        pool_setting = (self._project_settings["deadline"]
                                              ["publish"]
                                              ["CollectDeadlinePools"])

        primary_pool = pool_setting["primary_pool"]
        sorted_pools = self._set_default_pool(list(pools), primary_pool)
        cmds.addAttr(self.instance, longName="primaryPool",
                     attributeType="enum",
                     enumName=":".join(sorted_pools))

        pools = ["-"] + pools
        secondary_pool = pool_setting["secondary_pool"]
        sorted_pools = self._set_default_pool(list(pools), secondary_pool)
        cmds.addAttr("{}.secondaryPool".format(self.instance),
                     attributeType="enum",
                     enumName=":".join(sorted_pools))

    def _create_render_settings(self):
        """Create instance settings."""
        # get pools (slave machines of the render farm)
        pool_names = []
        default_priority = 50

        self.server_aliases = list(self.deadline_servers.keys())
        self.data["deadlineServers"] = self.server_aliases
        self.data["suspendPublishJob"] = False
        self.data["review"] = True
        self.data["extendFrames"] = False
        self.data["overrideExistingFrame"] = True
        # self.data["useLegacyRenderLayers"] = True
        self.data["priority"] = default_priority
        self.data["tile_priority"] = default_priority
        self.data["framesPerTask"] = 1
        self.data["whitelist"] = False
        self.data["machineList"] = ""
        self.data["useMayaBatch"] = False
        self.data["tileRendering"] = False
        self.data["tilesX"] = 2
        self.data["tilesY"] = 2
        self.data["convertToScanline"] = False
        self.data["useReferencedAovs"] = False
        # Disable for now as this feature is not working yet
        # self.data["assScene"] = False

        system_settings = get_system_settings()["modules"]

        deadline_enabled = system_settings["deadline"]["enabled"]
        muster_enabled = system_settings["muster"]["enabled"]
        muster_url = system_settings["muster"]["MUSTER_REST_URL"]

        if deadline_enabled and muster_enabled:
            self.log.error(
                "Both Deadline and Muster are enabled. " "Cannot support both."
            )
            raise RuntimeError("Both Deadline and Muster are enabled")

        if deadline_enabled:
            try:
                deadline_url = self.deadline_servers["default"]
            except KeyError:
                # if 'default' server is not between selected,
                # use first one for initial list of pools.
                deadline_url = next(iter(self.deadline_servers.values()))
            # Uses function to get pool machines from the assigned deadline
            # url in settings
            pool_names = self.deadline_module.get_deadline_pools(deadline_url,
                                                                  self.log)
            maya_submit_dl = self._project_settings.get(
                "deadline", {}).get(
                "publish", {}).get(
                "MayaSubmitDeadline", {})
            priority = maya_submit_dl.get("priority", default_priority)
            self.data["priority"] = priority

            tile_priority = maya_submit_dl.get("tile_priority",
                                               default_priority)
            self.data["tile_priority"] = tile_priority

        if muster_enabled:
            self.log.info(">>> Loading Muster credentials ...")
            self._load_credentials()
            self.log.info(">>> Getting pools ...")
            pools = []
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
            for pool in pools:
                self.log.info("  - pool: {}".format(pool["name"]))
                pool_names.append(pool["name"])

        pool_setting = (self._project_settings["deadline"]
                                              ["publish"]
                                              ["CollectDeadlinePools"])
        primary_pool = pool_setting["primary_pool"]
        self.data["primaryPool"] = self._set_default_pool(pool_names,
                                                          primary_pool)
        # We add a string "-" to allow the user to not
        # set any secondary pools
        pool_names = ["-"] + pool_names
        secondary_pool = pool_setting["secondary_pool"]
        self.data["secondaryPool"] = self._set_default_pool(pool_names,
                                                            secondary_pool)
        self.options = {"useSelection": False}  # Force no content

    def _set_default_pool(self, pool_names, pool_value):
        """Reorder pool names, default should come first"""
        if pool_value and pool_value in pool_names:
            pool_names.remove(pool_value)
            pool_names = [pool_value] + pool_names
        return pool_names

    def _load_credentials(self):
        """Load Muster credentials.

        Load Muster credentials from file and set ``MUSTER_USER``,
        ``MUSTER_PASSWORD``, ``MUSTER_REST_URL`` is loaded from settings.

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
        login_response = requests_get(api_url, timeout=1)
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
            kwargs["verify"] = not os.getenv("OPENPYPE_DONT_VERIFY_SSL", True)
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
            kwargs["verify"] = not os.getenv("OPENPYPE_DONT_VERIFY_SSL", True)
        return requests.get(*args, **kwargs)
