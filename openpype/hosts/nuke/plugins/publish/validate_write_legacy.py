import toml

import nuke

import pyblish.api
import openpype.api
from openpype.pipeline import discover_creator_plugins
from openpype.hosts.nuke.api.lib import get_avalon_knob_data


class ValidateWriteLegacy(pyblish.api.InstancePlugin):
    """Validate legacy write nodes."""

    order = pyblish.api.ValidatorOrder
    optional = True
    families = ["write"]
    label = "Validate Write Legacy"
    hosts = ["nuke"]
    actions = [openpype.api.RepairAction]

    def process(self, instance):
        node = instance[0]
        msg = "Clean up legacy write node \"{}\"".format(instance)

        if node.Class() not in ["Group", "Write"]:
            return

        # test avalon knobs
        family_knobs = ["ak:family", "avalon:family"]
        family_test = [k for k in node.knobs().keys() if k in family_knobs]
        self.log.debug("_ family_test: {}".format(family_test))

        # test if render in family test knob
        # and only one item should be available
        assert len(family_test) == 1, msg + " > More avalon attributes"
        assert "render" in node[family_test[0]].value() \
            or "still" in node[family_test[0]].value(), msg + \
            " > Not correct family"
        # test if `file` knob in node, this way old
        # non-group-node write could be detected
        assert "file" not in node.knobs(), msg + \
            " > file knob should not be present"

        # check if write node is having old render targeting
        assert "render_farm" not in node.knobs(), msg + \
            " > old way of setting render target"

    @classmethod
    def repair(cls, instance):
        node = instance[0]

        if "Write" in node.Class():
            data = toml.loads(node["avalon"].value())
        else:
            data = get_avalon_knob_data(node)

        # collect reusable data
        data["XYpos"] = (node.xpos(), node.ypos())
        data["input"] = node.input(0)
        data["publish"] = node["publish"].value()
        data["render"] = node["render"].value()
        data["render_farm"] = node["render_farm"].value()
        data["review"] = node["review"].value()
        data["use_limit"] = node["use_limit"].value()
        data["first"] = node["first"].value()
        data["last"] = node["last"].value()

        family = data["family"]
        cls.log.debug("_ orig node family: {}".format(family))

        # define what family of write node should be recreated
        if family == "render":
            Create_name = "CreateWriteRender"
        elif family == "prerender":
            Create_name = "CreateWritePrerender"
        elif family == "still":
            Create_name = "CreateWriteStill"

        # get appropriate plugin class
        creator_plugin = None
        for Creator in discover_creator_plugins():
            if Creator.__name__ != Create_name:
                continue

            creator_plugin = Creator

        # delete the legaci write node
        nuke.delete(node)

        # create write node with creator
        new_node_name = data["subset"]
        creator_plugin(new_node_name, data["asset"]).process()

        node = nuke.toNode(new_node_name)
        node.setXYpos(*data["XYpos"])
        node.setInput(0, data["input"])
        node["publish"].setValue(data["publish"])
        node["review"].setValue(data["review"])
        node["use_limit"].setValue(data["use_limit"])
        node["first"].setValue(data["first"])
        node["last"].setValue(data["last"])

        # recreate render targets
        if data["render"]:
            node["render"].setValue("Local")
            if data["render_farm"]:
                node["render"].setValue("On farm")
