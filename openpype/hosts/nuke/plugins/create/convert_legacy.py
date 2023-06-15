from openpype.pipeline.create.creator_plugins import SubsetConvertorPlugin
from openpype.hosts.nuke.api.lib import (
    INSTANCE_DATA_KNOB,
    get_node_data,
    get_avalon_knob_data,
    AVALON_TAB,
)
from openpype.hosts.nuke.api.plugin import convert_to_valid_instaces

import nuke


class LegacyConverted(SubsetConvertorPlugin):
    identifier = "legacy.converter"

    def find_instances(self):

        legacy_found = False
        # search for first available legacy item
        for node in nuke.allNodes(recurseGroups=True):
            if node.Class() in ["Viewer", "Dot"]:
                continue

            if get_node_data(node, INSTANCE_DATA_KNOB):
                continue

            if AVALON_TAB not in node.knobs():
                continue

            # get data from avalon knob
            avalon_knob_data = get_avalon_knob_data(
                node, ["avalon:", "ak:"], create=False)

            if not avalon_knob_data:
                continue

            if avalon_knob_data["id"] != "pyblish.avalon.instance":
                continue

            # catch and break
            legacy_found = True
            break

        if legacy_found:
            # if not item do not add legacy instance converter
            self.add_convertor_item("Convert legacy instances")

    def convert(self):
        # loop all instances and convert them
        convert_to_valid_instaces()
        # remove legacy item if all is fine
        self.remove_convertor_item()
