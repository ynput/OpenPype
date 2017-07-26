import pyblish.api


class DebugPlugin(pyblish.api.InstancePlugin):

    label = "Debug"
    order = pyblish.api.IntegratorOrder - 0.4

    def process(self, instance):

        import pprint

        self.log("\n\n----------------------")
        self.log("Instance")
        pprint.pprint(instance)
