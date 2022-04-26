import pyblish
import nuke


class FixProxyMode(pyblish.api.Action):
    """
    Togger off proxy switch OFF
    """

    label = "Proxy toggle to OFF"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):
        rootNode = nuke.root()
        rootNode["proxy"].setValue(False)


@pyblish.api.log
class ValidateProxyMode(pyblish.api.ContextPlugin):
    """Validate active proxy mode"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Proxy Mode"
    hosts = ["nuke"]
    actions = [FixProxyMode]

    def process(self, context):

        rootNode = nuke.root()
        isProxy = rootNode["proxy"].value()

        assert not isProxy, "Proxy mode should be toggled OFF"
