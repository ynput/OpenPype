import pyblish

class DetermineFutureVersion(pyblish.api.InstancePlugin):
    """
    This will determine version of subset if we want render to be attached to.
    """
    label = "Determine Subset Version"
    order = pyblish.api.IntegratorOrder
    hosts = ["maya"]
    families = ["renderlayer"]

    def process(self, instance):
        context = instance.context
        attach_to_subsets = [s["subset"] for s in instance.data['attachTo']]

        if not attach_to_subsets:
            return

        for i in context:
            if i.data["subset"] in attach_to_subsets:
                # # this will get corresponding subset in attachTo list
                # # so we can set version there
                sub = next(item for item in instance.data['attachTo'] if item["subset"] == i.data["subset"])  # noqa: E501

                sub["version"] = i.data.get("version", 1)
                self.log.info("render will be attached to {} v{}".format(
                        sub["subset"], sub["version"]
                ))
