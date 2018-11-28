import avalon.api
import avalon.nuke
from pype.nuke import (
    create_write_node
)
from pype import api as pype

log = pype.Logger.getLogger(__name__, "nuke")


class CrateWriteRender(avalon.nuke.Creator):
    name = "WriteRender"
    label = "Create Write Render"
    hosts = ["nuke"]
    family = "render"
    icon = "sign-out"

    def process(self):
        instance = super(CrateWriteRender, self).process()

        if not instance:
            data_templates = {
                "cls": "write",
                "family": self.family
            }
            create_write_node(self.name, self.data, data_templates)
        return


class CrateWritePrerender(avalon.nuke.Creator):
    name = "WritePrerender"
    label = "Create Write Prerender"
    hosts = ["nuke"]
    family = "prerender"
    icon = "sign-out"

    def process(self):
        instance = super(CrateWritePrerender, self).process()

        if not instance:
            data_templates = {
                "cls": "write",
                "family": self.family
            }
            create_write_node(self.name, self.data, data_templates)
        return None


class CrateWriteStill(avalon.nuke.Creator):
    name = "WriteStill"
    label = "Create Write Still"
    hosts = ["nuke"]
    family = "still"
    icon = "image"

    def process(self):
        instance = super(CrateWriteStill, self).process()

        if not instance:
            data_templates = {
                "cls": "write",
                "family": self.family
            }
            create_write_node(self.name, self.data, data_templates)
        return
