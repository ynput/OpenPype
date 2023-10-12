from openpype.hosts.maya.api import plugin, lib
from openpype.lib import (
    BoolDef,
    EnumDef,
    TextDef
)

from maya import cmds


class CreateMayaUsd(plugin.MayaCreator):
    """Create Maya USD Export"""

    identifier = "io.openpype.creators.maya.mayausd"
    label = "Maya USD"
    family = "usd"
    icon = "cubes"
    description = "Create Maya USD Export"

    cache = {}

    # TODO: Remove these default variants - this is just to trivialize
    #   the usage of the bootstrapping that was once built for Houdini
    #   that bootstrapped usdModel and usdShade as usdAsset
    default_variants = ["Model", "Shade"]

    def get_publish_families(self):
        return ["usd", "mayaUsd"]

    def get_instance_attr_defs(self):

        if "jobContextItems" not in self.cache:
            # Query once instead of per instance
            job_context_items = {}
            try:
                cmds.loadPlugin("mayaUsdPlugin", quiet=True)
                job_context_items = {
                    cmds.mayaUSDListJobContexts(jobContext=name): name
                    for name in cmds.mayaUSDListJobContexts(export=True) or []
                }
            except RuntimeError:
                # Likely `mayaUsdPlugin` plug-in not available
                self.log.warning("Unable to retrieve available job "
                                 "contexts for `mayaUsdPlugin` exports")

            if not job_context_items:
                # enumdef multiselection may not be empty
                job_context_items = ["<placeholder; do not use>"]

            self.cache["jobContextItems"] = job_context_items

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
                    tooltip=(
                        "Remove namespaces during export. By default, "
                        "namespaces are exported to the USD file in the "
                        "following format: nameSpaceExample_pPlatonic1"
                    ),
                    default=True),
            BoolDef("mergeTransformAndShape",
                    label="Merge Transform and Shape",
                    tooltip=(
                        "Combine Maya transform and shape into a single USD"
                        "prim that has transform and geometry, for all"
                        " \"geometric primitives\" (gprims).\n"
                        "This results in smaller and faster scenes. Gprims "
                        "will be \"unpacked\" back into transform and shape "
                        "nodes when imported into Maya from USD."
                    ),
                    default=True),
            BoolDef("includeUserDefinedAttributes",
                    label="Include User Defined Attributes",
                    tooltip=(
                        "Whether to include all custom maya attributes found "
                        "on nodes as metadata (userProperties) in USD."
                    ),
                    default=False),
            TextDef("attr",
                    label="Custom Attributes",
                    default="",
                    placeholder="attr1, attr2"),
            TextDef("attrPrefix",
                    label="Custom Attributes Prefix",
                    default="",
                    placeholder="prefix1, prefix2"),
            EnumDef("jobContext",
                    label="Job Context",
                    items=self.cache["jobContextItems"],
                    tooltip=(
                        "Specifies an additional export context to handle.\n"
                        "These usually contain extra schemas, primitives,\n"
                        "and materials that are to be exported for a "
                        "specific\ntask, a target renderer for example."
                    ),
                    multiselection=True),
        ])

        return defs


class CreateMayaUsdContribution(CreateMayaUsd):


    identifier = "io.openpype.creators.maya.mayausd.contribution"
    label = "Maya USD Contribution"
    family = "usd.layered"
    icon = "cubes"
    description = "Create Maya USD Contribution"

    def get_instance_attr_defs(self):

        import os
        defs = super(CreateMayaUsdContribution, self).get_instance_attr_defs()
        defs.insert(0, TextDef(
            "sublayer",
            label="Sublayer",
            default=os.environ["AVALON_TASK"]
        ))
        return defs
