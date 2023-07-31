import os
import requests
import six
import sys

from openpype.lib import requests_get, Logger
from openpype.modules import OpenPypeModule, IPluginPaths


class DeadlineWebserviceError(Exception):
    """
    Exception to throw when connection to Deadline server fails.
    """


class DeadlineModule(OpenPypeModule, IPluginPaths):
    name = "deadline"

    def __init__(self, manager, settings):
        self.deadline_urls = {}
        super(DeadlineModule, self).__init__(manager, settings)

    def initialize(self, modules_settings):
        # This module is always enabled
        deadline_settings = modules_settings[self.name]
        self.enabled = deadline_settings[0]['enabled']
        deadline_url = deadline_settings[0].get("DEADLINE_REST_URL")

        if deadline_url:
            self.deadline_urls = {"default": deadline_url}
        else:
            self.deadline_urls = deadline_settings[0].get("deadline_urls")  # noqa: E501

        if not self.deadline_urls:
            self.enabled = False
            self.log.warning(("default Deadline Webservice URL "
                              "not specified. Disabling module."))
            return

    def get_plugin_paths(self):
        """Deadline plugin paths."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return {
            "publish": [os.path.join(current_dir, "plugins", "publish")],
            "actions": [os.path.join(current_dir, "actions")],
        }

    @staticmethod
    def get_deadline_pools(webservice, log=None):
        # type: (str) -> list
        """Get pools from Deadline.
        Args:
            webservice (str): Server url.
            log (Logger)
        Returns:
            list: Pools.
        Throws:
            RuntimeError: If deadline webservice is unreachable.

        """
        if not log:
            log = Logger.get_logger(__name__)

        argument = "{}/api/pools?NamesOnly=true".format(webservice)
        try:
            response = requests_get(argument)
        except requests.exceptions.ConnectionError as exc:
            msg = 'Cannot connect to DL web service {}'.format(webservice)
            log.error(msg)
            six.reraise(
                DeadlineWebserviceError,
                DeadlineWebserviceError('{} - {}'.format(msg, exc)),
                sys.exc_info()[2])
        if not response.ok:
            log.warning("No pools retrieved")
            return []

        return response.json()
