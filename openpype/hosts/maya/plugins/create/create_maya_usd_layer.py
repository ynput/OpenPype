from openpype.hosts.maya.api import plugin
from openpype.lib import EnumDef


class CreateMayaUsdLayer(plugin.MayaCreator):
    """Create Maya USD Export from `mayaUsdProxyShape` layer"""

    identifier = "io.openpype.creators.maya.mayausdlayer"
    label = "Maya USD Layer Export"
    family = "usd"
    icon = "cubes"
    description = "Create mayaUsdProxyShape layer export"

    def get_publish_families(self):
        return ["usd", "mayaUsdLayer"]

    def get_instance_attr_defs(self):

        from maya import cmds
        import mayaUsd

        items = []
        for proxy in cmds.ls(type="mayaUsdProxyShape", long=True):
            # Ignore unsharable proxies
            if not cmds.getAttr(proxy + ".shareStage"):
                continue

            stage = mayaUsd.ufe.getStage("|world{}".format(proxy))
            if not stage:
                continue

            for layer in stage.GetLayerStack(includeSessionLayers=False):

                proxy_nice_name = proxy.rsplit("|", 2)[-2]
                layer_nice_name = layer.GetDisplayName()
                label = "{} -> {}".format(proxy_nice_name, layer_nice_name)
                value = ">".join([proxy, layer.identifier])

                items.append({
                    "label": label,
                    "value": value
                })

        if not items:
            items.append("<NONE>")

        defs = [
            EnumDef("defaultUSDFormat",
                    label="File format",
                    items={
                        "usdc": "Binary",
                        "usda": "ASCII"
                    },
                    default="usdc"),
            EnumDef("stageLayerIdentifier",
                    label="Stage and Layer Identifier",
                    items=items)
        ]

        return defs
