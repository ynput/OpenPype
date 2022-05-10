from openpype.hosts.maya.api import plugin, lib


class CreateMultiverseUsd(plugin.Creator):
    """Create Multiverse USD Asset"""

    name = "usdMain"
    label = "Multiverse USD"
    family = "usd"
    icon = "cubes"

    def __init__(self, *args, **kwargs):
        super(CreateMultiverseUsd, self).__init__(*args, **kwargs)

        # Add animation data first, since it maintains order.
        self.data.update(lib.collect_animation_data(True))

        self.data["fileFormat"] = ["usd", "usda", "usdz"]
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
        self.data["numTimeSamples"] = 1
        self.data["timeSamplesSpan"] = 0.0
