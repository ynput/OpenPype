import toml
import os

import nuke

from avalon import api
import re
import pyblish.api
from avalon.nuke import get_avalon_knob_data

class RepairWriteLegacyAction(pyblish.api.Action):

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):

        # Get the errored instances
        failed = []
        for result in context.data["results"]:
            if (result["error"] is not None and result["instance"] is not None
               and result["instance"] not in failed):
                failed.append(result["instance"])

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(failed, plugin)

        for instance in instances:
            if "Write" in instance[0].Class():
                data = toml.loads(instance[0]["avalon"].value())
            else:
                data = get_avalon_knob_data(instance[0])

            self.log.info(data)

            data["xpos"] = instance[0].xpos()
            data["ypos"] = instance[0].ypos()
            data["input"] = instance[0].input(0)
            data["publish"] = instance[0]["publish"].value()
            data["render"] = instance[0]["render"].value()
            data["render_farm"] = instance[0]["render_farm"].value()
            data["review"] = instance[0]["review"].value()

            # nuke.delete(instance[0])

            task = os.environ["AVALON_TASK"]
            sanitized_task = re.sub('[^0-9a-zA-Z]+', '', task)
            subset_name = "render{}Main".format(
                sanitized_task.capitalize())

            Create_name = "CreateWriteRender"

            creator_plugin = None
            for Creator in api.discover(api.Creator):
                if Creator.__name__ != Create_name:
                    continue

                creator_plugin = Creator

            # return api.create()
            creator_plugin(data["subset"], data["asset"]).process()

            node = nuke.toNode(data["subset"])
            node.setXYpos(data["xpos"], data["ypos"])
            node.setInput(0, data["input"])
            node["publish"].setValue(data["publish"])
            node["render"].setValue(data["render"])
            node["render_farm"].setValue(data["render_farm"])
            node["review"].setValue(data["review"])


class ValidateWriteLegacy(pyblish.api.InstancePlugin):
    """Validate legacy write nodes."""

    order = pyblish.api.ValidatorOrder
    optional = True
    families = ["write.legacy"]
    label = "Write Legacy"
    hosts = ["nuke"]
    actions = [RepairWriteLegacyAction]

    def process(self, instance):

        msg = "Clean up legacy write node \"{}\"".format(instance)
        assert False, msg
