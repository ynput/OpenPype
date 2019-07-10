from collections import OrderedDict
import avalon.api
import avalon.nuke
from pype.nuke import (
    create_write_node
)
from pype import api as pype
# from pypeapp import Logger

import nuke


log = pype.Logger().get_logger(__name__, "nuke")


def subset_to_families(subset, family, families):
    subset_sufx = str(subset).replace(family, "")
    new_subset = families + subset_sufx
    return "{}.{}".format(family, new_subset)


class CreateWriteRender(avalon.nuke.Creator):
    # change this to template preset
    preset = "render"

    name = "WriteRender"
    label = "Create Write Render"
    hosts = ["nuke"]
    family = "{}_write".format(preset)
    families = preset
    icon = "sign-out"
    defaults = ["Main", "Mask"]

    def __init__(self, *args, **kwargs):
        super(CreateWriteRender, self).__init__(*args, **kwargs)

        data = OrderedDict()

        data["family"] = self.family.split("_")[-1]
        data["families"] = self.families

        {data.update({k: v}) for k, v in self.data.items()
         if k not in data.keys()}
        self.data = data

    def process(self):
        self.name = self.data["subset"]

        family = self.family
        node = 'write'

        instance = nuke.toNode(self.data["subset"])

        if not instance:
            write_data = {
                "class": node,
                "preset": self.preset,
                "avalon": self.data
            }

            create_write_node(self.data["subset"], write_data)

        return


class CreateWritePrerender(avalon.nuke.Creator):
    # change this to template preset
    preset = "prerender"

    name = "WritePrerender"
    label = "Create Write Prerender"
    hosts = ["nuke"]
    family = "{}_write".format(preset)
    families = preset
    icon = "sign-out"
    defaults = ["Main", "Mask"]

    def __init__(self, *args, **kwargs):
        super(CreateWritePrerender, self).__init__(*args, **kwargs)

        data = OrderedDict()

        data["family"] = self.family.split("_")[1]
        data["families"] = self.families

        {data.update({k: v}) for k, v in self.data.items()
         if k not in data.keys()}
        self.data = data

    def process(self):
        self.name = self.data["subset"]

        instance = nuke.toNode(self.data["subset"])
        node = 'write'

        if not instance:
            write_data = {
                "class": node,
                "preset": self.preset,
                "avalon": self.data
            }

            create_write_node(self.data["subset"], write_data)

        return


"""
class CrateWriteStill(avalon.nuke.Creator):
    # change this to template preset
    preset = "still"

    name = "WriteStill"
    label = "Create Write Still"
    hosts = ["nuke"]
    family = "{}_write".format(preset)
    families = preset
    icon = "image"

    def __init__(self, *args, **kwargs):
        super(CrateWriteStill, self).__init__(*args, **kwargs)

        data = OrderedDict()

        data["family"] = self.family.split("_")[-1]
        data["families"] = self.families

        {data.update({k: v}) for k, v in self.data.items()
         if k not in data.keys()}
        self.data = data

    def process(self):
        self.name = self.data["subset"]

        node_name = self.data["subset"].replace(
            "_", "_f{}_".format(nuke.frame()))
        instance = nuke.toNode(self.data["subset"])
        self.data["subset"] = node_name

        family = self.family
        node = 'write'

        if not instance:
            write_data = {
                "frame_range": [nuke.frame(), nuke.frame()],
                "class": node,
                "preset": self.preset,
                "avalon": self.data
            }

            nuke.createNode("FrameHold", "first_frame {}".format(nuke.frame()))
            create_write_node(node_name, write_data)

        return
"""
