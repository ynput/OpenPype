from openpype.hosts.maya.api import plugin, lib
from openpype.lib import (
    BoolDef,
    NumberDef,
    TextDef,
    EnumDef
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
            # BoolDef("writeAncestors",
            #         label="Write Ancestors",
            #         default=True),
            # BoolDef("flattenParentXforms",
            #         label="Flatten Parent Xforms",
            #         default=False),
            # BoolDef("writeSparseOverrides",
            #         label="Write Sparse Overrides",
            #         default=False),
            # BoolDef("useMetaPrimPath",
            #         label="Use Meta Prim Path",
            #         default=False),
            # TextDef("customRootPath",
            #         label="Custom Root Path",
            #         default=''),
            # TextDef("customAttributes",
            #         label="Custom Attributes",
            #         tooltip="Comma-separated list of attribute names",
            #         default=''),
            # TextDef("nodeTypesToIgnore",
            #         label="Node Types to Ignore",
            #         tooltip="Comma-separated list of node types to be ignored",
            #         default=''),
            # BoolDef("writeMeshes",
            #         label="Write Meshes",
            #         default=True),
            # BoolDef("writeCurves",
            #         label="Write Curves",
            #         default=True),
            # BoolDef("writeParticles",
            #         label="Write Particles",
            #         default=True),
            # BoolDef("writeCameras",
            #         label="Write Cameras",
            #         default=False),
            # BoolDef("writeLights",
            #         label="Write Lights",
            #         default=False),
            # BoolDef("writeJoints",
            #         label="Write Joints",
            #         default=False),
            # BoolDef("writeCollections",
            #         label="Write Collections",
            #         default=False),
            # BoolDef("writePositions",
            #         label="Write Positions",
            #         default=True),
            # BoolDef("writeNormals",
            #         label="Write Normals",
            #         default=True),
            # BoolDef("writeUVs",
            #         label="Write UVs",
            #         default=True),
            # BoolDef("writeColorSets",
            #         label="Write Color Sets",
            #         default=False),
            # BoolDef("writeTangents",
            #         label="Write Tangents",
            #         default=False),
            # BoolDef("writeRefPositions",
            #         label="Write Ref Positions",
            #         default=True),
            # BoolDef("writeBlendShapes",
            #         label="Write BlendShapes",
            #         default=False),
            # BoolDef("writeDisplayColor",
            #         label="Write Display Color",
            #         default=True),
            # BoolDef("writeSkinWeights",
            #         label="Write Skin Weights",
            #         default=False),
            # BoolDef("writeMaterialAssignment",
            #         label="Write Material Assignment",
            #         default=False),
            # BoolDef("writeHardwareShader",
            #         label="Write Hardware Shader",
            #         default=False),
            # BoolDef("writeShadingNetworks",
            #         label="Write Shading Networks",
            #         default=False),
            # BoolDef("writeTransformMatrix",
            #         label="Write Transform Matrix",
            #         default=True),
            # BoolDef("writeUsdAttributes",
            #         label="Write USD Attributes",
            #         default=True),
            # BoolDef("writeInstancesAsReferences",
            #         label="Write Instances as References",
            #         default=False),
            # BoolDef("timeVaryingTopology",
            #         label="Time Varying Topology",
            #         default=False),
            # TextDef("customMaterialNamespace",
            #         label="Custom Material Namespace",
            #         default=''),
            # NumberDef("numTimeSamples",
            #           label="Num Time Samples",
            #           default=1),
            # NumberDef("timeSamplesSpan",
            #           label="Time Samples Span",
            #           default=0.0),
            #
        ])

        return defs
