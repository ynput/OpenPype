import random
import string

import avalon.nuke
from avalon.nuke import lib as anlib
from avalon import api

from openpype.api import (
    get_current_project_settings,
    PypeCreatorMixin
)
from .lib import check_subsetname_exists
import nuke


class PypeCreator(PypeCreatorMixin, avalon.nuke.pipeline.Creator):
    """Pype Nuke Creator class wrapper
    """
    def __init__(self, *args, **kwargs):
        super(PypeCreator, self).__init__(*args, **kwargs)
        self.presets = get_current_project_settings()["nuke"]["create"].get(
            self.__class__.__name__, {}
        )
        if check_subsetname_exists(
                nuke.allNodes(),
                self.data["subset"]):
            msg = ("The subset name `{0}` is already used on a node in"
                   "this workfile.".format(self.data["subset"]))
            self.log.error(msg + '\n\nPlease use other subset name!')
            raise NameError("`{0}: {1}".format(__name__, msg))
        return


def get_review_presets_config():
    settings = get_current_project_settings()
    review_profiles = (
        settings["global"]
        ["publish"]
        ["ExtractReview"]
        ["profiles"]
    )

    outputs = {}
    for profile in review_profiles:
        outputs.update(profile.get("outputs", {}))

    return [str(name) for name, _prop in outputs.items()]


class NukeLoader(api.Loader):
    container_id_knob = "containerId"
    container_id = None

    def reset_container_id(self):
        self.container_id = ''.join(random.choice(
            string.ascii_uppercase + string.digits) for _ in range(10))

    def get_container_id(self, node):
        id_knob = node.knobs().get(self.container_id_knob)
        return id_knob.value() if id_knob else None

    def get_members(self, source):
        """Return nodes that has same 'containerId' as `source`"""
        source_id = self.get_container_id(source)
        return [node for node in nuke.allNodes(recurseGroups=True)
                if self.get_container_id(node) == source_id
                and node is not source] if source_id else []

    def set_as_member(self, node):
        source_id = self.get_container_id(node)

        if source_id:
            node[self.container_id_knob].setValue(source_id)
        else:
            HIDEN_FLAG = 0x00040000
            _knob = anlib.Knobby(
                "String_Knob",
                self.container_id,
                flags=[
                    nuke.READ_ONLY,
                    HIDEN_FLAG
                ])
            knob = _knob.create(self.container_id_knob)
            node.addKnob(knob)

    def clear_members(self, parent_node):
        members = self.get_members(parent_node)

        dependent_nodes = None
        for node in members:
            _depndc = [n for n in node.dependent() if n not in members]
            if not _depndc:
                continue

            dependent_nodes = _depndc
            break

        for member in members:
            self.log.info("removing node: `{}".format(member.name()))
            nuke.delete(member)

        return dependent_nodes
