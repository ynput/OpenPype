from openpype.hosts.maya.api import plugin, lib
from openpype.lib import (
    BoolDef,
    EnumDef,
    TextDef
)


class CreateMayaUsd(plugin.MayaCreator):
    """Create Maya USD Export"""

    identifier = "io.openpype.creators.maya.mayausd"
    label = "Maya USD"
    family = "usd"
    icon = "cubes"
    description = "Create Maya USD Export"

    def get_publish_families(self):
        return ["usd", "mayaUsd"]

    def get_instance_attr_defs(self):

        defs = lib.collect_animation_defs()
        defs.extend([
            EnumDef("defaultUSDFormat",
                    label="File format",
                    items={
                        "usdc": "Binary",
                        "usda": "ASCII"
                    },
                    default="usdc"),
            BoolDef("stripNamespaces",
                    label="Strip Namespaces",
                    default=True),
            BoolDef("mergeTransformAndShape",
                    label="Merge Transform and Shape",
                    default=True),
            BoolDef("includeUserDefinedAttributes",
                    label="Include User Defined Attributes",
                    default=False),
            TextDef("attr",
                    label="Custom Attributes",
                    default="",
                    placeholder="attr1, attr2"),
            TextDef("attrPrefix",
                    label="Custom Attributes Prefix",
                    default="",
                    placeholder="prefix1, prefix2")
        ])

        return defs
