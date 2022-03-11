from openpype.hosts.maya.api import plugin, lib


class CreateMultiverseUsd(plugin.Creator):
    """Multiverse USD data"""

    name = "usdMain"
    label = "Multiverse USD"
    family = "usd"
    icon = "cubes"

    def __init__(self, *args, **kwargs):
        super(CreateMultiverseUsd, self).__init__(*args, **kwargs)

        self.data["stripNamespaces"] = False
        self.data["mergeTransformAndShape"] = False
        self.data["writeAncestors"] = True
        self.data["flattenParentXforms"] = False
        self.data["writeSparseOverrides"] = False
        self.data["useMetaPrimPath"] = False
        self.data["customRootPath"] = ''
        self.data["customAttributes"] = ''
        self.data["nodeTypesToIgnore"] = ''
        self.data["writeMeshes"] = True
        self.data["writeCurves"] = True
        self.data["writeParticles"] = True
        self.data["writeCameras"] = False
        self.data["writeLights"] = False
        self.data["writeJoints"] = False
        self.data["writeCollections"] = False
        self.data["writePositions"] = True
        self.data["writeNormals"] = True
        self.data["writeUVs"] = True
        self.data["writeColorSets"] = False
        self.data["writeTangents"] = False
        self.data["writeRefPositions"] = False
        self.data["writeBlendShapes"] = False
        self.data["writeDisplayColor"] = False
        self.data["writeSkinWeights"] = False
        self.data["writeMaterialAssignment"] = False
        self.data["writeHardwareShader"] = False
        self.data["writeShadingNetworks"] = False
        self.data["writeTransformMatrix"] = True
        self.data["writeUsdAttributes"] = False
        self.data["timeVaryingTopology"] = False
        self.data["customMaterialNamespace"] = ''

        # The attributes below are about animated cache.
        self.data["writeTimeRange"] = True
        self.data["timeRangeNumTimeSamples"] = 0
        self.data["timeRangeSamplesSpan"] = 0.0

        animation_data = lib.collect_animation_data(True)

        self.data["timeRangeStart"] = animation_data["frameStart"]
        self.data["timeRangeEnd"] = animation_data["frameEnd"]
        self.data["timeRangeIncrement"] = animation_data["step"]
        self.data["timeRangeFramesPerSecond"] = animation_data["fps"]
