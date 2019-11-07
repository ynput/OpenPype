from collections import OrderedDict
import avalon.api
import avalon.nuke
from pype import api as pype
from pype.nuke import plugin
from pypeapp import config

import nuke


log = pype.Logger().get_logger(__name__, "nuke")


class CreateWriteRender(plugin.PypeCreator):
    # change this to template preset
    name = "WriteRender"
    label = "Create Write Render"
    hosts = ["nuke"]
    nClass = "write"
    family = "render"
    icon = "sign-out"
    defaults = ["Main", "Mask"]

    def __init__(self, *args, **kwargs):
        super(CreateWriteRender, self).__init__(*args, **kwargs)

        self.name = self.data["subset"]

        data = OrderedDict()

        data["family"] = self.nClass
        data["families"] = self.family

        for k, v in self.data.items():
            if k not in data.keys():
                data.update({k: v})

        self.data = data
        self.log.info("_>>_ self.data: '{}'".format(self.data))

    def process(self):
        from pype.nuke import lib as pnlib
        reload(pnlib)
        instance = nuke.toNode(self.data["subset"])

        if not instance:
            write_data = {
                "class": self.nClass,
                "families": [self.family],
                "avalon": self.data
            }

            if self.presets.get('fpath_template'):
                self.log.info("Adding template path from preset")
                write_data.update(
                    {"fpath_template": self.presets["fpath_template"]}
                )
            else:
                self.log.info("Adding template path from plugin")
                write_data.update({
                    "fpath_template": "{work}/renders/nuke/{subset}/{subset}.{frame}.{ext}"})
        else:
            # collect input / outputs
            # remove old one
            # recreate new
            # relinking to collected connections
            return

        return pnlib.create_write_node(self.data["subset"], write_data)


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
        self.presets = config.get_presets()['plugins']["nuke"]["create"].get(
            self.__class__.__name__, {}
        )

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

            if self.presets.get('fpath_template'):
                self.log.info("Adding template path from preset")
                write_data.update(
                    {"fpath_template": self.presets["fpath_template"]}
                )
            else:
                self.log.info("Adding template path from plugin")
                write_data.update({
                    "fpath_template": "{work}/prerenders/{subset}/{subset}.{frame}.{ext}"})

            # get group node
            group_node = create_write_node(self.data["subset"], write_data)

            # open group node
            group_node.begin()
            for n in nuke.allNodes():
                # get write node
                if n.Class() in "Write":
                    write_node = n
            group_node.end()

            # linking knobs to group property panel
            linking_knobs = ["first", "last", "use_limit"]
            for k in linking_knobs:
                lnk = nuke.Link_Knob(k)
                lnk.makeLink(write_node.name(), k)
                lnk.setName(k.replace('_', ' ').capitalize())
                lnk.clearFlag(nuke.STARTLINE)
                group_node.addKnob(lnk)

        return
