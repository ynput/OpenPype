import os
import json

import appdirs

import pyblish.api
from openpype.lib import requests_get
from openpype.plugin import contextplugin_should_run
import openpype.hosts.maya.api.action


class ValidateMusterConnection(pyblish.api.ContextPlugin):
    """
    Validate Muster REST API Service is running and we have valid auth token
    """

    label = "Validate Muster REST API Service"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    families = ["renderlayer"]
    token = None
    if not os.environ.get("MUSTER_REST_URL"):
        active = False
    actions = [openpype.api.RepairAction]

    def process(self, context):

        # Workaround bug pyblish-base#250
        if not contextplugin_should_run(self, context):
            return

        # test if we have environment set (redundant as this plugin shouldn'
        # be active otherwise).
        try:
            MUSTER_REST_URL = os.environ["MUSTER_REST_URL"]
        except KeyError:
            self.log.error("Muster REST API url not found.")
            raise ValueError("Muster REST API url not found.")

        # Load credentials
        try:
            self._load_credentials()
        except RuntimeError:
            self.log.error("invalid or missing access token")

        assert self._token is not None, "Invalid or missing token"

        # We have token, lets do trivial query to web api to see if we can
        # connect and access token is valid.
        params = {
            'authToken': self._token
        }
        api_entry = '/api/pools/list'
        response = requests_get(
            MUSTER_REST_URL + api_entry, params=params)
        assert response.status_code == 200, "invalid response from server"
        assert response.json()['ResponseData'], "invalid data in response"

    def _load_credentials(self):
        """
        Load Muster credentials from file and set `MUSTER_USER`,
        `MUSTER_PASSWORD`, `MUSTER_REST_URL` is loaded from settings.

        .. todo::

           Show login dialog if access token is invalid or missing.
        """
        app_dir = os.path.normpath(
            appdirs.user_data_dir('pype-app', 'pype')
        )
        file_name = 'muster_cred.json'
        fpath = os.path.join(app_dir, file_name)
        file = open(fpath, 'r')
        muster_json = json.load(file)
        self._token = muster_json.get('token', None)
        if not self._token:
            raise RuntimeError("Invalid access token for Muster")
        file.close()
        self.MUSTER_REST_URL = os.environ.get("MUSTER_REST_URL")
        if not self.MUSTER_REST_URL:
            raise AttributeError("Muster REST API url not set")

    @classmethod
    def repair(cls, instance):
        """
        Renew authentication token by logging into Muster
        """
        api_url = "{}/muster/show_login".format(
            os.environ["OPENPYPE_WEBSERVER_URL"])
        cls.log.debug(api_url)
        response = requests_get(api_url, timeout=1)
        if response.status_code != 200:
            cls.log.error('Cannot show login form to Muster')
            raise Exception('Cannot show login form to Muster')
