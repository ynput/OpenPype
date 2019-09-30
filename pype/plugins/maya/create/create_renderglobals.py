from maya import cmds

import pype.maya.lib as lib

from avalon.vendor import requests
import avalon.maya
import os
import json
import appdirs


class CreateRenderGlobals(avalon.maya.Creator):

    label = "Render Globals"
    family = "renderglobals"
    icon = "gears"
    defaults = ['Main']

    _token = None
    _user = None
    _password = None

    def __init__(self, *args, **kwargs):
        super(CreateRenderGlobals, self).__init__(*args, **kwargs)

        # We won't be publishing this one
        self.data["id"] = "avalon.renderglobals"

        # get pools
        pools = []

        deadline_url = os.environ.get('DEADLINE_REST_URL', None)
        muster_url = os.environ.get('MUSTER_REST_URL', None)
        if deadline_url and muster_url:
            self.log.error("Both Deadline and Muster are enabled. "
                           "Cannot support both.")
            raise RuntimeError("Both Deadline and Muster are enabled")

        if deadline_url is None:
            self.log.warning("Deadline REST API url not found.")
        else:
            argument = "{}/api/pools?NamesOnly=true".format(deadline_url)
            response = requests.get(argument)
            if not response.ok:
                self.log.warning("No pools retrieved")
            else:
                pools = response.json()
                self.data["primaryPool"] = pools
                # We add a string "-" to allow the user to not
                # set any secondary pools
                self.data["secondaryPool"] = ["-"] + pools

        if muster_url is None:
            self.log.warning("Muster REST API url not found.")
        else:
            self.log.info(">>> Loading Muster credentials ...")
            self._load_credentials()
            self.log.info(">>> Logging in Muster ...")
            self._authenticate()
            self.log.info(">>> Getting pools ...")
            pools = self._get_muster_pools()
            pool_names = []
            for pool in pools:
                self.log.info("  - pool: {}".format(pool['name']))
                pool_names.append(pool['name'])

            self.data["primaryPool"] = pool_names

        # We don't need subset or asset attributes
        # self.data.pop("subset", None)
        # self.data.pop("asset", None)
        # self.data.pop("active", None)

        self.data["suspendPublishJob"] = False
        self.data["extendFrames"] = False
        self.data["overrideExistingFrame"] = True
        self.data["useLegacyRenderLayers"] = True
        self.data["priority"] = 50
        self.data["framesPerTask"] = 1
        self.data["whitelist"] = False
        self.data["machineList"] = ""
        self.data["useMayaBatch"] = True

        self.options = {"useSelection": False}  # Force no content

    def process(self):

        exists = cmds.ls(self.name)
        assert len(exists) <= 1, (
            "More than one renderglobal exists, this is a bug"
        )

        if exists:
            return cmds.warning("%s already exists." % exists[0])

        with lib.undo_chunk():
            super(CreateRenderGlobals, self).process()
            cmds.setAttr("{}.machineList".format(self.name), lock=True)

    def _load_credentials(self):
        """
        Load Muster credentials from file and set `MUSTER_USER`,
        `MUSTER_PASSWORD`, `MUSTER_REST_URL` is loaded from presets.
        """
        app_dir = os.path.normpath(
            appdirs.user_data_dir('pype-app', 'pype')
        )
        file_name = 'muster_cred.json'
        fpath = os.path.join(app_dir, file_name)
        file = open(fpath, 'r')
        muster_json = json.load(file)
        self.MUSTER_USER = muster_json.get('username', None)
        self.MUSTER_PASSWORD = muster_json.get('password', None)
        file.close()
        self.MUSTER_REST_URL = os.environ.get("MUSTER_REST_URL")
        if not self.MUSTER_REST_URL:
            raise AttributeError("Muster REST API url not set")

    def _authenticate(self):
        """
        Authenticate user with Muster and get authToken from server.
        """
        params = {
                    'username': self.MUSTER_USER,
                    'password': self.MUSTER_PASSWORD
               }
        api_entry = '/api/login'
        response = requests.post(
            self.MUSTER_REST_URL + api_entry, params=params)
        if response.status_code != 200:
            self.log.error(
                'Cannot log into Muster: {}'.format(response.status_code))
            raise Exception('Cannot login into Muster.')

        try:
            self._token = response.json()['ResponseData']['authToken']
        except ValueError as e:
            self.log.error('Invalid response from Muster server {}'.format(e))
            raise Exception('Invalid response from Muster while logging in.')

        return self._token

    def _get_muster_pools(self):
        """
        Get render pools from muster
        """
        params = {
                'authToken': self._token
            }
        api_entry = '/api/pools/list'
        response = requests.post(
            self.MUSTER_REST_URL + api_entry, params=params)
        if response.status_code != 200:
            self.log.error(
                'Cannot get pools from Muster: {}'.format(
                    response.status_code))
            raise Exception('Cannot get pools from Muster')
        try:
            pools = response.json()['ResponseData']['pools']
        except ValueError as e:
            self.log.error('Invalid response from Muster server {}'.format(e))
            raise Exception('Invalid response from Muster server')

        return pools
