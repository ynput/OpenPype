import ast
import re
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

        self.plugin_paths = {}
        for valid_plugin_type in self._valid_plugin_types:
            self.plugin_paths[valid_plugin_type] = {
                'all': []
            }

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

        # Retrieve plugin paths and properly sort them
        hosts_regex = re.compile(r'hosts = (?P<hosts>\[[^\]]+\])')
        plugin_dir = Path(__file__).joinpath("plugins").resolve()

        for valid_plugin_type in self._valid_plugin_types:
            search_dir = plugin_dir.joinpath(valid_plugin_type)

            if not search_dir.exists():
                continue

            dir_plugin_paths = list(search_dir.glob('*.py'))

            for plugin_path_str in dir_plugin_paths:
                plugin_path = Path(plugin_path_str).resolve()
                plugin_path_resolved = str(plugin_path)

                # Opening the file, reading the content and extracting
                # the list of hosts for the plugin path
                with open(plugin_path) as f:
                    content = f.read()
                    match = hosts_regex.search(content)

                    if not match or not match.lastgroup:
                        # The regex didn't match, maybe an __init__.py file
                        continue

                    hosts_str = re.sub(r'\s+', '', match.group(match.lastgroup))
                    hosts_list = ast.literal_eval(hosts_str)

                    # Adding the plugin path to the "all" array
                    self.plugin_paths[valid_plugin_type]['all'].append(plugin_path_resolved)

                    # Adding the plugin path to the correct host array(s)
                    for host in hosts_list:
                        if host in self.plugin_paths[valid_plugin_type]:
                            self.plugin_paths[valid_plugin_type][host].append(plugin_path_resolved)
                        else:
                            self.plugin_paths[valid_plugin_type][host] = [plugin_path_resolved]

    def get_plugin_paths(self):
        """Deadline plugin paths."""
        all_plugin_paths = {}

        for valid_plugin_type in self._valid_plugin_types:
            all_plugin_paths[valid_plugin_type] = self.plugin_paths[valid_plugin_type]['all']

        return all_plugin_paths

    def get_publish_plugin_paths(self, host_name):
        """Only get the plugin paths related to the host specified"""
        if not host_name or host_name not in self.plugin_paths['publish']:
            # If we cannot determine the host, or it's not specified,
            # then we will return all the registered plugin paths
            host_name = "all"

        return self.plugin_paths['publish'][host_name]

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
