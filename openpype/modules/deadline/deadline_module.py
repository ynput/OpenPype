import os
import requests
import six
import sys
from pathlib import Path

from openpype.lib import requests_get, Logger
from openpype.modules import OpenPypeModule, IPluginPaths


class DeadlineWebserviceError(Exception):
    """
    Exception to throw when connection to Deadline server fails.
    """


class DeadlineModule(OpenPypeModule, IPluginPaths):
    name = "deadline"
    _valid_plugin_types = ["publish"]

    def __init__(self, manager, settings):
        self.deadline_urls = {}
        self._plugin_folders = {}
        super(DeadlineModule, self).__init__(manager, settings)

    def initialize(self, modules_settings):
        # This module is always enabled
        deadline_settings = modules_settings[self.name]
        self.enabled = deadline_settings["enabled"]
        deadline_url = deadline_settings.get("DEADLINE_REST_URL")
        if deadline_url:
            self.deadline_urls = {"default": deadline_url}
        else:
            self.deadline_urls = deadline_settings.get("deadline_urls")  # noqa: E501

        if not self.deadline_urls:
            self.enabled = False
            self.log.warning(("default Deadline Webservice URL "
                              "not specified. Disabling module."))
            return

    def get_plugin_folders(self, regenerate_cache=False):
        if self._plugin_folders and not regenerate_cache:
            return self._plugin_folders

        parent_folder_path = Path(__file__).parent

        hosts_folders_iterator = parent_folder_path.glob('*/')
        for host_folder_path in hosts_folders_iterator:
            host_name = host_folder_path.stem

            if host_name not in self._plugin_folders:
                self._plugin_folders[host_name] = {}

            for plugin_type_path in host_folder_path.glob('*/'):
                type_name = plugin_type_path.stem

                if type_name not in self._valid_plugin_types:
                    continue

                if type_name not in self._plugin_folders[host_name]:
                    self._plugin_folders[host_name][type_name] = []

                self._plugin_folders[host_name][type_name].append(str(plugin_type_path.absolute()))

        return self._plugin_folders

    def get_plugin_paths(self):
        """Implementation of abstract method for `IPluginPaths`."""
        plugin_folders = self.get_plugin_folders()

        # Initialize all plugins which can be supported
        plugins_dict = {type_name: [] for type_name in self._valid_plugin_types}

        for host_name in plugin_folders:
            for type_name in plugin_folders[host_name]:
                if type_name in plugins_dict:
                    plugins_dict[type_name].extend(plugin_folders[host_name][type_name])

        return plugins_dict

    def get_plugin_paths_by_hostnames_and_type(self, host_names, type_name):
        plugins_paths = []

        plugin_folders = self.get_plugin_folders()

        if isinstance(host_names, str):
            host_names = [host_names]

        for host_name in host_names:
            if host_name in plugin_folders and type_name in plugin_folders[host_name]:
                plugins_paths.extend(plugin_folders[host_name][type_name])

        return plugins_paths

    def get_publish_plugin_paths(self, host_name):
        return self.get_plugin_paths_by_hostnames_and_type([host_name, "common"], "publish")

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
        if not webservice:
            return []

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

    @staticmethod
    def get_deadline_data(webservice, endpoint, log=None, **kwargs):
        """Get Limits groups for Deadline
        Args:
            webservice (str): Server url
            endpoint (str): Request endpoint
            log (Logger)
            kwargs (Any): Request payload content as key=value pairs
        Returns:
            Any: Returns the json-encoded content of a response, if any.
        Throws:
            RuntimeError: If Deadline webservice is unreachable.
        """
        if not log:
            log = Logger.get_logger(__name__)

        request = "{}/api/{}".format(
            webservice,
            endpoint
        )

        # Construct the full request with arguments
        arguments = []
        for key, value in kwargs.items():
            new_argument = "{}={}".format(key, value)
            arguments.append(new_argument)

        if arguments:
            arguments = "&".join(arguments)
            request = "{}?{}".format(request, arguments)

        try:
            response = requests_get(request)
        except requests.exceptions.ConnectionError as exc:
            msg = "Cannot connect to DL web service {}".format(webservice)
            log.error(msg)
            six.reraise(
                DeadlineWebserviceError,
                DeadlineWebserviceError("{} - {}".format(msg, exc)),
                sys.exc_info()[2]
            )
        if not response.ok:
            log.warning("The data requested could not be retrieved")
            return []

        return response.json()
