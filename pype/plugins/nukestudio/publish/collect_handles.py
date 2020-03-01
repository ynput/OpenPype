from pyblish import api


class CollectClipHandles(api.ContextPlugin):
    """Collect Handles from all instanes and add to assetShared."""

    order = api.CollectorOrder + 0.0121
    label = "Collect Handles"
    hosts = ["nukestudio"]

    def process(self, context):
        assets_shared = context.data.get("assetsShared")

        # find all main types instances and add its handles to asset shared
        instances = context[:]
        filtered_instances = []
        for instance in instances:
            self.log.debug("_ instance.name: `{}`".format(instance.data["name"]))
            families = instance.data.get("families", [])
            families += [instance.data["family"]]
            if "clip" in families:
                filtered_instances.append(instance)
            else:
                continue

            # get handles
            handle_start = int(instance.data["handleStart"])
            handle_end = int(instance.data["handleEnd"])

            if instance.data.get("main"):
                name = instance.data["asset"]
                if assets_shared.get(name):
                    asset_shared = assets_shared.get(name)
                else:
                    asset_shared = assets_shared[name]

                self.log.debug("Adding to shared assets: `{}`".format(
                    instance.data["name"]))
                asset_shared.update({
                    "handleStart": handle_start,
                    "handleEnd": handle_end
                })

        for instance in filtered_instances:
            if not instance.data.get("main") and not instance.data.get("handleTag"):
                self.log.debug("Synchronize handles on: `{}`".format(
                    instance.data["name"]))
                name = instance.data["asset"]
                s_asset_data = assets_shared.get(name)
                instance.data["handleStart"] = s_asset_data.get(
                    "handleStart", 0
                )
                instance.data["handleEnd"] = s_asset_data.get("handleEnd", 0)

                # debug printing
                self.log.debug("_ s_asset_data: `{}`".format(
                    s_asset_data))
                self.log.debug("_ instance.data[handleStart]: `{}`".format(
                    instance.data["handleStart"]))
                self.log.debug("_ instance.data[handleEnd]: `{}`".format(
                    instance.data["handleEnd"]))
