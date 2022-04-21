import os
import copy

from openpype.api import get_project_settings


def initialize():
    from openpype.hosts.traypublisher.api.plugin import SettingsCreator

    project_name = os.environ["AVALON_PROJECT"]
    project_settings = get_project_settings(project_name)

    simple_creators = project_settings["traypublisher"]["simple_creators"]

    global_variables = globals()
    for item in simple_creators:
        allow_sequences_value = item["allow_sequences"]
        allow_sequences = allow_sequences_value["allow"]
        if allow_sequences == "all":
            sequence_extensions = copy.deepcopy(item["extensions"])

        elif allow_sequences == "no":
            sequence_extensions = []

        elif allow_sequences == "selection":
            sequence_extensions = allow_sequences_value["extensions"]

        item["sequence_extensions"] = sequence_extensions
        item["enable_review"] = False
        dynamic_plugin = SettingsCreator.from_settings(item)
        global_variables[dynamic_plugin.__name__] = dynamic_plugin


initialize()
