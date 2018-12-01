from collections import OrderedDict
import avalon.api
import avalon.nuke
from pype.nuke import (
    create_write_node
)
from pype import api as pype


log = pype.Logger.getLogger(__name__, "nuke")


def subset_to_families(subset, family, families):
    subset_sufx = str(subset).replace(family, "")
    new_subset = families + subset_sufx
    return "{}.{}".format(family, new_subset)


class CrateWriteRender(avalon.nuke.Creator):
    # change this to template preset
    preset = "render"

    name = "WriteRender"
    label = "Create Write Render"
    hosts = ["nuke"]
    family = "{}.write".format(preset)
    families = preset
    icon = "sign-out"

    def __init__(self, *args, **kwargs):
        super(CrateWriteRender, self).__init__(*args, **kwargs)

        data = OrderedDict()

        data["family"] = self.family.split(".")[1]
        data["families"] = self.families

        {data.update({k: v}) for k, v in self.data.items()
         if k not in data.keys()}
        self.data = data

    def process(self):
        self.data["subset"] = "{}.{}".format(self.families, self.data["subset"])
        self.name = self.data["subset"]

        instance = super(CrateWriteRender, self).process()

        family = self.family.split(".")[0]
        node = self.family.split(".")[1]

        if not instance:
            write_data = {
                "class": node,
                "preset": family,
                "avalon": self.data
            }

            create_write_node(self.data["subset"], write_data)

        return


class CrateWritePrerender(avalon.nuke.Creator):
    # change this to template preset
    preset = "prerender"

    name = "WritePrerender"
    label = "Create Write Prerender"
    hosts = ["nuke"]
    family = "{}.write".format(preset)
    families = preset
    icon = "sign-out"

    def __init__(self, *args, **kwargs):
        super(CrateWritePrerender, self).__init__(*args, **kwargs)

        data = OrderedDict()

        data["family"] = self.family.split(".")[1]
        data["families"] = self.families

        {data.update({k: v}) for k, v in self.data.items()
         if k not in data.keys()}
        self.data = data

    def process(self):
        self.data["subset"] = "{}.{}".format(self.families, self.data["subset"])
        self.name = self.data["subset"]

        instance = super(CrateWritePrerender, self).process()

        family = self.family.split(".")[0]
        node = self.family.split(".")[1]

        if not instance:
            write_data = {
                "class": node,
                "preset": family,
                "avalon": self.data
            }

            create_write_node(self.data["subset"], write_data)

        return


class CrateWriteStill(avalon.nuke.Creator):
    # change this to template preset
    preset = "still"

    name = "WriteStill"
    label = "Create Write Still"
    hosts = ["nuke"]
    family = "{}.write".format(preset)
    families = preset
    icon = "image"

    def __init__(self, *args, **kwargs):
        super(CrateWriteStill, self).__init__(*args, **kwargs)

        data = OrderedDict()

        data["family"] = self.family.split(".")[1]
        data["families"] = self.families

        {data.update({k: v}) for k, v in self.data.items()
         if k not in data.keys()}
        self.data = data

    def process(self):
        import nuke
        self.data["subset"] = "{}.{}".format(self.families, self.data["subset"])
        self.name = self.data["subset"]

        instance = super(CrateWriteStill, self).process()

        family = self.family.split(".")[0]
        node = self.family.split(".")[1]

        if not instance:
            write_data = {
                "frame_range": [nuke.frame(), nuke.frame()],
                "class": node,
                "preset": family,
                "avalon": self.data
            }

            nuke.createNode("FrameHold", "first_frame {}".format(nuke.frame()))
            create_write_node(self.data["subset"], write_data)

        return
