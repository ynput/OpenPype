from ayon_server.settings import BaseSettingsModel, SettingsField


class PluginsModel(BaseSettingsModel):
    _layout = "expanded"
    enabled: bool = SettingsField(title="Enabled")
    name: str = SettingsField("", title="Name")


class ExplicitPluginsLoadingModel(BaseSettingsModel):
    """Maya Explicit Plugins Loading."""
    _isGroup: bool = True
    enabled: bool = SettingsField(title="enabled")
    plugins_to_load: list[PluginsModel] = SettingsField(
        default_factory=list, title="Plugins To Load"
    )


DEFAULT_EXPLITCIT_PLUGINS_LOADING_SETTINGS = {
    "enabled": False,
    "plugins_to_load": [
        {
            "enabled": False,
            "name": "AbcBullet"
        },
        {
            "enabled": True,
            "name": "AbcExport"
        },
        {
            "enabled": True,
            "name": "AbcImport"
        },
        {
            "enabled": False,
            "name": "animImportExport"
        },
        {
            "enabled": False,
            "name": "ArubaTessellator"
        },
        {
            "enabled": False,
            "name": "ATFPlugin"
        },
        {
            "enabled": False,
            "name": "atomImportExport"
        },
        {
            "enabled": False,
            "name": "AutodeskPacketFile"
        },
        {
            "enabled": False,
            "name": "autoLoader"
        },
        {
            "enabled": False,
            "name": "bifmeshio"
        },
        {
            "enabled": False,
            "name": "bifrostGraph"
        },
        {
            "enabled": False,
            "name": "bifrostshellnode"
        },
        {
            "enabled": False,
            "name": "bifrostvisplugin"
        },
        {
            "enabled": False,
            "name": "blast2Cmd"
        },
        {
            "enabled": False,
            "name": "bluePencil"
        },
        {
            "enabled": False,
            "name": "Boss"
        },
        {
            "enabled": False,
            "name": "bullet"
        },
        {
            "enabled": True,
            "name": "cacheEvaluator"
        },
        {
            "enabled": False,
            "name": "cgfxShader"
        },
        {
            "enabled": False,
            "name": "cleanPerFaceAssignment"
        },
        {
            "enabled": False,
            "name": "clearcoat"
        },
        {
            "enabled": False,
            "name": "convertToComponentTags"
        },
        {
            "enabled": False,
            "name": "curveWarp"
        },
        {
            "enabled": False,
            "name": "ddsFloatReader"
        },
        {
            "enabled": True,
            "name": "deformerEvaluator"
        },
        {
            "enabled": False,
            "name": "dgProfiler"
        },
        {
            "enabled": False,
            "name": "drawUfe"
        },
        {
            "enabled": False,
            "name": "dx11Shader"
        },
        {
            "enabled": False,
            "name": "fbxmaya"
        },
        {
            "enabled": False,
            "name": "fltTranslator"
        },
        {
            "enabled": False,
            "name": "freeze"
        },
        {
            "enabled": False,
            "name": "Fur"
        },
        {
            "enabled": False,
            "name": "gameFbxExporter"
        },
        {
            "enabled": False,
            "name": "gameInputDevice"
        },
        {
            "enabled": False,
            "name": "GamePipeline"
        },
        {
            "enabled": False,
            "name": "gameVertexCount"
        },
        {
            "enabled": False,
            "name": "geometryReport"
        },
        {
            "enabled": False,
            "name": "geometryTools"
        },
        {
            "enabled": False,
            "name": "glslShader"
        },
        {
            "enabled": True,
            "name": "GPUBuiltInDeformer"
        },
        {
            "enabled": False,
            "name": "gpuCache"
        },
        {
            "enabled": False,
            "name": "hairPhysicalShader"
        },
        {
            "enabled": False,
            "name": "ik2Bsolver"
        },
        {
            "enabled": False,
            "name": "ikSpringSolver"
        },
        {
            "enabled": False,
            "name": "invertShape"
        },
        {
            "enabled": False,
            "name": "lges"
        },
        {
            "enabled": False,
            "name": "lookdevKit"
        },
        {
            "enabled": False,
            "name": "MASH"
        },
        {
            "enabled": False,
            "name": "matrixNodes"
        },
        {
            "enabled": False,
            "name": "mayaCharacterization"
        },
        {
            "enabled": False,
            "name": "mayaHIK"
        },
        {
            "enabled": False,
            "name": "MayaMuscle"
        },
        {
            "enabled": False,
            "name": "mayaUsdPlugin"
        },
        {
            "enabled": False,
            "name": "mayaVnnPlugin"
        },
        {
            "enabled": False,
            "name": "melProfiler"
        },
        {
            "enabled": False,
            "name": "meshReorder"
        },
        {
            "enabled": True,
            "name": "modelingToolkit"
        },
        {
            "enabled": False,
            "name": "mtoa"
        },
        {
            "enabled": False,
            "name": "mtoh"
        },
        {
            "enabled": False,
            "name": "nearestPointOnMesh"
        },
        {
            "enabled": True,
            "name": "objExport"
        },
        {
            "enabled": False,
            "name": "OneClick"
        },
        {
            "enabled": False,
            "name": "OpenEXRLoader"
        },
        {
            "enabled": False,
            "name": "pgYetiMaya"
        },
        {
            "enabled": False,
            "name": "pgyetiVrayMaya"
        },
        {
            "enabled": False,
            "name": "polyBoolean"
        },
        {
            "enabled": False,
            "name": "poseInterpolator"
        },
        {
            "enabled": False,
            "name": "quatNodes"
        },
        {
            "enabled": False,
            "name": "randomizerDevice"
        },
        {
            "enabled": False,
            "name": "redshift4maya"
        },
        {
            "enabled": True,
            "name": "renderSetup"
        },
        {
            "enabled": False,
            "name": "retargeterNodes"
        },
        {
            "enabled": False,
            "name": "RokokoMotionLibrary"
        },
        {
            "enabled": False,
            "name": "rotateHelper"
        },
        {
            "enabled": False,
            "name": "sceneAssembly"
        },
        {
            "enabled": False,
            "name": "shaderFXPlugin"
        },
        {
            "enabled": False,
            "name": "shotCamera"
        },
        {
            "enabled": False,
            "name": "snapTransform"
        },
        {
            "enabled": False,
            "name": "stage"
        },
        {
            "enabled": True,
            "name": "stereoCamera"
        },
        {
            "enabled": False,
            "name": "stlTranslator"
        },
        {
            "enabled": False,
            "name": "studioImport"
        },
        {
            "enabled": False,
            "name": "Substance"
        },
        {
            "enabled": False,
            "name": "substancelink"
        },
        {
            "enabled": False,
            "name": "substancemaya"
        },
        {
            "enabled": False,
            "name": "substanceworkflow"
        },
        {
            "enabled": False,
            "name": "svgFileTranslator"
        },
        {
            "enabled": False,
            "name": "sweep"
        },
        {
            "enabled": False,
            "name": "testify"
        },
        {
            "enabled": False,
            "name": "tiffFloatReader"
        },
        {
            "enabled": False,
            "name": "timeSliderBookmark"
        },
        {
            "enabled": False,
            "name": "Turtle"
        },
        {
            "enabled": False,
            "name": "Type"
        },
        {
            "enabled": False,
            "name": "udpDevice"
        },
        {
            "enabled": False,
            "name": "ufeSupport"
        },
        {
            "enabled": False,
            "name": "Unfold3D"
        },
        {
            "enabled": False,
            "name": "VectorRender"
        },
        {
            "enabled": False,
            "name": "vrayformaya"
        },
        {
            "enabled": False,
            "name": "vrayvolumegrid"
        },
        {
            "enabled": False,
            "name": "xgenToolkit"
        },
        {
            "enabled": False,
            "name": "xgenVray"
        }
    ]
}
