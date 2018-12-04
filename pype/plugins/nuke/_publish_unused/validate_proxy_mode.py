import nuke

import pyblish.api


class RepairNukeProxyModeAction(pyblish.api.Action):

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):

        nuke.root()["proxy"].setValue(0)


class ValidateNukeProxyMode(pyblish.api.ContextPlugin):
    """Validates against having proxy mode on."""

    order = pyblish.api.ValidatorOrder
    optional = True
    label = "Proxy Mode"
    actions = [RepairNukeProxyModeAction]
    hosts = ["nuke", "nukeassist"]
  # targets = ["default", "process"]

    def process(self, context):

        msg = (
            "Proxy mode is not supported. Please disable Proxy Mode in the "
            "Project settings."
        )
        assert not nuke.root()["proxy"].getValue(), msg
