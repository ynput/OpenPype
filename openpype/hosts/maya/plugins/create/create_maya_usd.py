from openpype.hosts.maya.api import plugin, lib
from openpype.lib import (
    BoolDef,
    EnumDef,
    TextDef,
    UILabelDef,
    UISeparatorDef,
    usdlib
)
from openpype.pipeline.context_tools import get_current_context

from maya import cmds


class CreateMayaUsd(plugin.MayaCreator):
    """Create Maya USD Export"""

    identifier = "io.openpype.creators.maya.mayausd"
    label = "Maya USD"
    family = "usd"
    icon = "cubes"
    description = "Create Maya USD Export"

    cache = {}

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
    """

    When writing a USD as 'contribution' it will be added into what it's
    contributing to. It will usually contribute to either the main *asset*
    or *shot* but can be customized.

    Usually the contribution is done into a Department Layer, like e.g.
    model, rig, look for models and layout, animation, fx, lighting for shots.

    Each department contribution will be 'sublayered' into the departments
    contribution.

    """

    identifier = "io.openpype.creators.maya.mayausd.contribution"
    label = "Maya USD Contribution"
    family = "usd"
    icon = "cubes"
    description = "Create Maya USD Contribution"

    def get_publish_families(self):
        families = ["usd", "mayaUsd", "usd.layered"]
        if self.family not in families:
            families.append(self.family)
        return families

    def get_instance_attr_defs(self):

        context = get_current_context()

        # The departments must be 'ordered' so that e.g. a look can apply
        # overrides to any opinion from the model department.
        department = context["task_name"]  # usually equals the department?
        variant = "Main"  # used as default for sublayer

        defs = [
            UISeparatorDef("contribution_settings1"),
            UILabelDef(label="<b>Contribution</b>"),
            UISeparatorDef("contribution_settings2"),
            BoolDef("contribution_enabled",
                    label="Add to USD container",
                    default=True),
            TextDef("contribution_department_layer",
                    label="Department layer",
                    default=department),
            TextDef("contribution_sublayer",
                    label="Sublayer",
                    # Usually e.g. usdModel, usdLook, usdLookRed
                    default=variant),
            TextDef("contribution_variant_set_name",
                    label="Variant Set Name",
                    default=""),
            TextDef("contribution_variant",
                    label="Variant Name",
                    default=""),
            UISeparatorDef("export_settings1"),
            UILabelDef(label="<b>Export Settings</b>"),
            UISeparatorDef("export_settings2"),
        ]
        defs += super(CreateMayaUsdContribution, self).get_instance_attr_defs()
        return defs


for contribution in usdlib.PIPELINE["asset"]:

    step = contribution.step

    class CreateMayaUsdDynamicStepContribution(CreateMayaUsdContribution):
        identifier = f"{CreateMayaUsdContribution.identifier}.{step}"
        default_variants = plugin.MayaCreator.default_variants
        label = f"USD {step.title()}"
        family = contribution.family

        # Define some nice icons
        icon = {
            "look": "paint-brush",
            "model": "cube",
            "rig": "wheelchair"
        }.get(step, "cubes")

        description = f"Create USD {step.title()} Contribution"

        bootstrap = "asset"

        contribution = contribution

        # TODO: Should these still be customizable
        # contribution_sublayer_order = contribution.order
        # contribution_department = contribution.step
        # contribution_variant_set_name = contribution.step
        # contribution_variant_name = "{variant}"

        def add_transient_instance_data(self, instance_data):
            super().add_transient_instance_data(instance_data)
            instance_data["usd_bootstrap"] = self.bootstrap
            instance_data["usd_contribution"] = self.contribution

        def remove_transient_instance_data(self, instance_data):
            super().remove_transient_instance_data(instance_data)
            instance_data.pop("usd_bootstrap", None)
            instance_data.pop("usd_contribution", None)

    # Dynamically create USD creators for easy access to a certain step
    # in production
    global_variables = globals()
    klass_name = f"CreateMayaUsd{step.title()}Contribution"
    klass = type(klass_name, (CreateMayaUsdDynamicStepContribution,), {})
    global_variables[klass_name] = klass

    # We only want to store the global variables, and don't want the last
    # iteration of the loop to persist after because Create Context will
    # pick those up too
    del klass
    del CreateMayaUsdDynamicStepContribution
