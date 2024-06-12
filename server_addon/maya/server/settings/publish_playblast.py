from pydantic import validator

from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    ensure_unique_names,
    task_types_enum,
)
from ayon_server.types import ColorRGBA_uint8


def hardware_falloff_enum():
    return [
        {"label": "Linear", "value": "0"},
        {"label": "Exponential", "value": "1"},
        {"label": "Exponential Squared", "value": "2"}
    ]


def renderer_enum():
    return [
        {"label": "Viewport 2.0", "value": "vp2Renderer"}
    ]


def displayLights_enum():
    return [
        {"label": "Default Lighting", "value": "default"},
        {"label": "All Lights", "value": "all"},
        {"label": "Selected Lights", "value": "selected"},
        {"label": "Flat Lighting", "value": "flat"},
        {"label": "No Lights", "value": "nolights"}
    ]


def plugin_objects_default():
    return [
        {
            "name": "gpuCacheDisplayFilter",
            "value": False
        }
    ]


class CodecSetting(BaseSettingsModel):
    _layout = "expanded"
    compression: str = SettingsField("png", title="Encoding")
    format: str = SettingsField("image", title="Format")
    quality: int = SettingsField(95, title="Quality", ge=0, le=100)


class DisplayOptionsSetting(BaseSettingsModel):
    _layout = "expanded"
    override_display: bool = SettingsField(
        True, title="Override display options"
    )
    background: ColorRGBA_uint8 = SettingsField(
        (125, 125, 125, 1.0), title="Background Color"
    )
    displayGradient: bool = SettingsField(
        True, title="Display background gradient"
    )
    backgroundTop: ColorRGBA_uint8 = SettingsField(
        (125, 125, 125, 1.0), title="Background Top"
    )
    backgroundBottom: ColorRGBA_uint8 = SettingsField(
        (125, 125, 125, 1.0), title="Background Bottom"
    )


class GenericSetting(BaseSettingsModel):
    _layout = "expanded"
    isolate_view: bool = SettingsField(True, title="Isolate View")
    off_screen: bool = SettingsField(True, title="Off Screen")
    pan_zoom: bool = SettingsField(False, title="2D Pan/Zoom")


class RendererSetting(BaseSettingsModel):
    _layout = "expanded"
    rendererName: str = SettingsField(
        "vp2Renderer",
        enum_resolver=renderer_enum,
        title="Renderer name"
    )


class ResolutionSetting(BaseSettingsModel):
    _layout = "expanded"
    width: int = SettingsField(0, title="Width")
    height: int = SettingsField(0, title="Height")


class PluginObjectsModel(BaseSettingsModel):
    name: str = SettingsField("", title="Name")
    value: bool = SettingsField(True, title="Enabled")


class ViewportOptionsSetting(BaseSettingsModel):
    override_viewport_options: bool = SettingsField(
        True, title="Override viewport options"
    )
    displayLights: str = SettingsField(
        "default", enum_resolver=displayLights_enum, title="Display Lights"
    )
    displayTextures: bool = SettingsField(True, title="Display Textures")
    textureMaxResolution: int = SettingsField(
        1024, title="Texture Clamp Resolution"
    )
    renderDepthOfField: bool = SettingsField(
        True, title="Depth of Field", section="Depth of Field"
    )
    shadows: bool = SettingsField(True, title="Display Shadows")
    twoSidedLighting: bool = SettingsField(True, title="Two Sided Lighting")
    lineAAEnable: bool = SettingsField(
        True, title="Enable Anti-Aliasing", section="Anti-Aliasing"
    )
    multiSample: int = SettingsField(8, title="Anti Aliasing Samples")
    loadTextures: bool = SettingsField(False, title="Load Textures")
    useDefaultMaterial: bool = SettingsField(
        False, title="Use Default Material"
    )
    wireframeOnShaded: bool = SettingsField(False, title="Wireframe On Shaded")
    xray: bool = SettingsField(False, title="X-Ray")
    jointXray: bool = SettingsField(False, title="X-Ray Joints")
    backfaceCulling: bool = SettingsField(False, title="Backface Culling")
    ssaoEnable: bool = SettingsField(
        False, title="Screen Space Ambient Occlusion", section="SSAO"
    )
    ssaoAmount: int = SettingsField(1, title="SSAO Amount")
    ssaoRadius: int = SettingsField(16, title="SSAO Radius")
    ssaoFilterRadius: int = SettingsField(16, title="SSAO Filter Radius")
    ssaoSamples: int = SettingsField(16, title="SSAO Samples")
    fogging: bool = SettingsField(
        False, title="Enable Hardware Fog", section="Fog"
    )
    hwFogFalloff: str = SettingsField(
        "0", enum_resolver=hardware_falloff_enum, title="Hardware Falloff"
    )
    hwFogDensity: float = SettingsField(0.0, title="Fog Density")
    hwFogStart: int = SettingsField(0, title="Fog Start")
    hwFogEnd: int = SettingsField(100, title="Fog End")
    hwFogAlpha: int = SettingsField(0, title="Fog Alpha")
    hwFogColorR: float = SettingsField(1.0, title="Fog Color R")
    hwFogColorG: float = SettingsField(1.0, title="Fog Color G")
    hwFogColorB: float = SettingsField(1.0, title="Fog Color B")
    motionBlurEnable: bool = SettingsField(
        False, title="Enable Motion Blur", section="Motion Blur"
    )
    motionBlurSampleCount: int = SettingsField(
        8, title="Motion Blur Sample Count"
    )
    motionBlurShutterOpenFraction: float = SettingsField(
        0.2, title="Shutter Open Fraction"
    )
    cameras: bool = SettingsField(False, title="Cameras", section="Show")
    clipGhosts: bool = SettingsField(False, title="Clip Ghosts")
    deformers: bool = SettingsField(False, title="Deformers")
    dimensions: bool = SettingsField(False, title="Dimensions")
    dynamicConstraints: bool = SettingsField(
        False, title="Dynamic Constraints"
    )
    dynamics: bool = SettingsField(False, title="Dynamics")
    fluids: bool = SettingsField(False, title="Fluids")
    follicles: bool = SettingsField(False, title="Follicles")
    greasePencils: bool = SettingsField(False, title="Grease Pencils")
    grid: bool = SettingsField(False, title="Grid")
    hairSystems: bool = SettingsField(True, title="Hair Systems")
    handles: bool = SettingsField(False, title="Handles")
    headsUpDisplay: bool = SettingsField(False, title="HUD")
    ikHandles: bool = SettingsField(False, title="IK Handles")
    imagePlane: bool = SettingsField(True, title="Image Plane")
    joints: bool = SettingsField(False, title="Joints")
    lights: bool = SettingsField(False, title="Lights")
    locators: bool = SettingsField(False, title="Locators")
    manipulators: bool = SettingsField(False, title="Manipulators")
    motionTrails: bool = SettingsField(False, title="Motion Trails")
    nCloths: bool = SettingsField(False, title="nCloths")
    nParticles: bool = SettingsField(False, title="nParticles")
    nRigids: bool = SettingsField(False, title="nRigids")
    controlVertices: bool = SettingsField(False, title="NURBS CVs")
    nurbsCurves: bool = SettingsField(False, title="NURBS Curves")
    hulls: bool = SettingsField(False, title="NURBS Hulls")
    nurbsSurfaces: bool = SettingsField(False, title="NURBS Surfaces")
    particleInstancers: bool = SettingsField(
        False, title="Particle Instancers"
    )
    pivots: bool = SettingsField(False, title="Pivots")
    planes: bool = SettingsField(False, title="Planes")
    pluginShapes: bool = SettingsField(False, title="Plugin Shapes")
    polymeshes: bool = SettingsField(True, title="Polygons")
    strokes: bool = SettingsField(False, title="Strokes")
    subdivSurfaces: bool = SettingsField(False, title="Subdiv Surfaces")
    textures: bool = SettingsField(False, title="Texture Placements")
    pluginObjects: list[PluginObjectsModel] = SettingsField(
        default_factory=plugin_objects_default,
        title="Plugin Objects"
    )

    @validator("pluginObjects")
    def validate_unique_plugin_objects(cls, value):
        ensure_unique_names(value)
        return value


class CameraOptionsSetting(BaseSettingsModel):
    displayGateMask: bool = SettingsField(False, title="Display Gate Mask")
    displayResolution: bool = SettingsField(False, title="Display Resolution")
    displayFilmGate: bool = SettingsField(False, title="Display Film Gate")
    displayFieldChart: bool = SettingsField(False, title="Display Field Chart")
    displaySafeAction: bool = SettingsField(False, title="Display Safe Action")
    displaySafeTitle: bool = SettingsField(False, title="Display Safe Title")
    displayFilmPivot: bool = SettingsField(False, title="Display Film Pivot")
    displayFilmOrigin: bool = SettingsField(False, title="Display Film Origin")
    overscan: int = SettingsField(1.0, title="Overscan")


class CapturePresetSetting(BaseSettingsModel):
    Codec: CodecSetting = SettingsField(
        default_factory=CodecSetting,
        title="Codec",
        section="Codec")
    DisplayOptions: DisplayOptionsSetting = SettingsField(
        default_factory=DisplayOptionsSetting,
        title="Display Options",
        section="Display Options")
    Generic: GenericSetting = SettingsField(
        default_factory=GenericSetting,
        title="Generic",
        section="Generic")
    Renderer: RendererSetting = SettingsField(
        default_factory=RendererSetting,
        title="Renderer",
        section="Renderer")
    Resolution: ResolutionSetting = SettingsField(
        default_factory=ResolutionSetting,
        title="Resolution",
        section="Resolution")
    ViewportOptions: ViewportOptionsSetting = SettingsField(
        default_factory=ViewportOptionsSetting,
        title="Viewport Options")
    CameraOptions: CameraOptionsSetting = SettingsField(
        default_factory=CameraOptionsSetting,
        title="Camera Options")


class ProfilesModel(BaseSettingsModel):
    _layout = "expanded"
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    task_names: list[str] = SettingsField(
        default_factory=list, title="Task names"
    )
    product_names: list[str] = SettingsField(
        default_factory=list, title="Products names"
    )
    capture_preset: CapturePresetSetting = SettingsField(
        default_factory=CapturePresetSetting,
        title="Capture Preset"
    )


class ExtractPlayblastSetting(BaseSettingsModel):
    capture_preset: CapturePresetSetting = SettingsField(
        default_factory=CapturePresetSetting,
        title="DEPRECATED! Please use \"Profiles\" below. Capture Preset"
    )
    profiles: list[ProfilesModel] = SettingsField(
        default_factory=list,
        title="Profiles"
    )


DEFAULT_PLAYBLAST_SETTING = {
    "capture_preset": {
        "Codec": {
            "compression": "png",
            "format": "image",
            "quality": 95
        },
        "DisplayOptions": {
            "override_display": True,
            "background": [
                125,
                125,
                125,
                1.0
            ],
            "backgroundBottom": [
                125,
                125,
                125,
                1.0
            ],
            "backgroundTop": [
                125,
                125,
                125,
                1.0
            ],
            "displayGradient": True
        },
        "Generic": {
            "isolate_view": True,
            "off_screen": True,
            "pan_zoom": False
        },
        "Renderer": {
            "rendererName": "vp2Renderer"
        },
        "Resolution": {
            "width": 1920,
            "height": 1080
        },
        "ViewportOptions": {
            "override_viewport_options": True,
            "displayLights": "default",
            "displayTextures": True,
            "textureMaxResolution": 1024,
            "renderDepthOfField": True,
            "shadows": True,
            "twoSidedLighting": True,
            "lineAAEnable": True,
            "multiSample": 8,
            "loadTextures": False,
            "useDefaultMaterial": False,
            "wireframeOnShaded": False,
            "xray": False,
            "jointXray": False,
            "backfaceCulling": False,
            "ssaoEnable": False,
            "ssaoAmount": 1,
            "ssaoRadius": 16,
            "ssaoFilterRadius": 16,
            "ssaoSamples": 16,
            "fogging": False,
            "hwFogFalloff": "0",
            "hwFogDensity": 0.0,
            "hwFogStart": 0,
            "hwFogEnd": 100,
            "hwFogAlpha": 0,
            "hwFogColorR": 1.0,
            "hwFogColorG": 1.0,
            "hwFogColorB": 1.0,
            "motionBlurEnable": False,
            "motionBlurSampleCount": 8,
            "motionBlurShutterOpenFraction": 0.2,
            "cameras": False,
            "clipGhosts": False,
            "deformers": False,
            "dimensions": False,
            "dynamicConstraints": False,
            "dynamics": False,
            "fluids": False,
            "follicles": False,
            "greasePencils": False,
            "grid": False,
            "hairSystems": True,
            "handles": False,
            "headsUpDisplay": False,
            "ikHandles": False,
            "imagePlane": True,
            "joints": False,
            "lights": False,
            "locators": False,
            "manipulators": False,
            "motionTrails": False,
            "nCloths": False,
            "nParticles": False,
            "nRigids": False,
            "controlVertices": False,
            "nurbsCurves": False,
            "hulls": False,
            "nurbsSurfaces": False,
            "particleInstancers": False,
            "pivots": False,
            "planes": False,
            "pluginShapes": False,
            "polymeshes": True,
            "strokes": False,
            "subdivSurfaces": False,
            "textures": False,
            "pluginObjects": [
                {
                    "name": "gpuCacheDisplayFilter",
                    "value": False
                }
            ]
        },
        "CameraOptions": {
            "displayGateMask": False,
            "displayResolution": False,
            "displayFilmGate": False,
            "displayFieldChart": False,
            "displaySafeAction": False,
            "displaySafeTitle": False,
            "displayFilmPivot": False,
            "displayFilmOrigin": False,
            "overscan": 1.0
        }
    },
    "profiles": []
}
