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
    name = "WriteRender"
    label = "Create Write Render"
    hosts = ["nuke"]
    family = "render"  # change this to template
    families = "write"  # do not change!
    icon = "sign-out"

    def __init__(self, *args, **kwargs):
        super(CrateWriteRender, self).__init__(*args, **kwargs)

        data = OrderedDict()

        # creating pype subset
        data["subset"] = subset_to_families(
            self.data["subset"],
            self.family,
            self.families
        )
        # swaping family with families
        data["family"] = self.families
        data["families"] = self.family

        {data.update({k: v}) for k, v in self.data.items()
         if k not in data.keys()}
        self.data = data

    def process(self):
        instance = super(CrateWriteRender, self).process()

        if not instance:
            data_templates = {
                "class": self.families,
                # only one is required
                "preset": self.family,
                "avalon": self.data
            }

            create_write_node(self.name, data_templates)

        return


class CrateWritePrerender(avalon.nuke.Creator):
    name = "WritePrerender"
    label = "Create Write Prerender"
    hosts = ["nuke"]
    family = "prerender"
    families = "write"
    icon = "sign-out"

    def __init__(self, *args, **kwargs):
        super(CrateWritePrerender, self).__init__(*args, **kwargs)

        data = OrderedDict()

        # creating pype subset
        data["subset"] = subset_to_families(
            self.data["subset"],
            self.family,
            self.families
        )
        # swaping family with families
        data["family"] = self.families
        data["families"] = self.family

        {data.update({k: v}) for k, v in self.data.items()
         if k not in data.keys()}
        self.data = data

    def process(self):
        instance = super(CrateWritePrerender, self).process()

        if not instance:
            data_templates = {
                "class": self.families,
                # only one is required
                "preset": self.family,
                "avalon": self.data
            }

            create_write_node(self.name, data_templates)

        return


class CrateWriteStill(avalon.nuke.Creator):
    name = "WriteStill"
    label = "Create Write Still"
    hosts = ["nuke"]
    family = "still"
    families = "write"
    icon = "image"

    def __init__(self, *args, **kwargs):
        super(CrateWriteStill, self).__init__(*args, **kwargs)

        data = OrderedDict()

        # creating pype subset
        data["subset"] = subset_to_families(
            self.data["subset"],
            self.family,
            self.families
        )
        # swaping family with families
        data["family"] = self.families
        data["families"] = self.family

        {data.update({k: v}) for k, v in self.data.items()
         if k not in data.keys()}
        self.data = data

    def process(self):
        instance = super(CrateWriteStill, self).process()

        if not instance:
            data_templates = {
                "class": self.families,
                # only one is required
                "preset": self.family,
                "avalon": self.data
            }

            create_write_node(self.name, data_templates)

        return
