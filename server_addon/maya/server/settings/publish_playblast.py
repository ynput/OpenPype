from pydantic import Field, validator

from ayon_server.settings import (
    BaseSettingsModel,
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
    compression: str = Field("png", title="Encoding")
    format: str = Field("image", title="Format")
    quality: int = Field(95, title="Quality", ge=0, le=100)


class DisplayOptionsSetting(BaseSettingsModel):
    _layout = "expanded"
    override_display: bool = Field(True, title="Override display options")
    background: ColorRGBA_uint8 = Field(
        (125, 125, 125, 1.0), title="Background Color"
    )
    displayGradient: bool = Field(True, title="Display background gradient")
    backgroundTop: ColorRGBA_uint8 = Field(
        (125, 125, 125, 1.0), title="Background Top"
    )
    backgroundBottom: ColorRGBA_uint8 = Field(
        (125, 125, 125, 1.0), title="Background Bottom"
    )


class GenericSetting(BaseSettingsModel):
    _layout = "expanded"
    isolate_view: bool = Field(True, title="Isolate View")
    off_screen: bool = Field(True, title="Off Screen")
    pan_zoom: bool = Field(False, title="2D Pan/Zoom")


class RendererSetting(BaseSettingsModel):
    _layout = "expanded"
    rendererName: str = Field(
        "vp2Renderer",
        enum_resolver=renderer_enum,
        title="Renderer name"
    )


class ResolutionSetting(BaseSettingsModel):
    _layout = "expanded"
    width: int = Field(0, title="Width")
    height: int = Field(0, title="Height")


class PluginObjectsModel(BaseSettingsModel):
    name: str = Field("", title="Name")
    value: bool = Field(True, title="Enabled")


class ViewportOptionsSetting(BaseSettingsModel):
    override_viewport_options: bool = Field(
        True, title="Override viewport options"
    )
    displayLights: str = Field(
        "default", enum_resolver=displayLights_enum, title="Display Lights"
    )
    displayTextures: bool = Field(True, title="Display Textures")
    textureMaxResolution: int = Field(1024, title="Texture Clamp Resolution")
    renderDepthOfField: bool = Field(
        True, title="Depth of Field", section="Depth of Field"
    )
    shadows: bool = Field(True, title="Display Shadows")
    twoSidedLighting: bool = Field(True, title="Two Sided Lighting")
    lineAAEnable: bool = Field(
        True, title="Enable Anti-Aliasing", section="Anti-Aliasing"
    )
    multiSample: int = Field(8, title="Anti Aliasing Samples")
    useDefaultMaterial: bool = Field(False, title="Use Default Material")
    wireframeOnShaded: bool = Field(False, title="Wireframe On Shaded")
    xray: bool = Field(False, title="X-Ray")
    jointXray: bool = Field(False, title="X-Ray Joints")
    backfaceCulling: bool = Field(False, title="Backface Culling")
    ssaoEnable: bool = Field(
        False, title="Screen Space Ambient Occlusion", section="SSAO"
    )
    ssaoAmount: int = Field(1, title="SSAO Amount")
    ssaoRadius: int = Field(16, title="SSAO Radius")
    ssaoFilterRadius: int = Field(16, title="SSAO Filter Radius")
    ssaoSamples: int = Field(16, title="SSAO Samples")
    fogging: bool = Field(False, title="Enable Hardware Fog", section="Fog")
    hwFogFalloff: str = Field(
        "0", enum_resolver=hardware_falloff_enum, title="Hardware Falloff"
    )
    hwFogDensity: float = Field(0.0, title="Fog Density")
    hwFogStart: int = Field(0, title="Fog Start")
    hwFogEnd: int = Field(100, title="Fog End")
    hwFogAlpha: int = Field(0, title="Fog Alpha")
    hwFogColorR: float = Field(1.0, title="Fog Color R")
    hwFogColorG: float = Field(1.0, title="Fog Color G")
    hwFogColorB: float = Field(1.0, title="Fog Color B")
    motionBlurEnable: bool = Field(
        False, title="Enable Motion Blur", section="Motion Blur"
    )
    motionBlurSampleCount: int = Field(8, title="Motion Blur Sample Count")
    motionBlurShutterOpenFraction: float = Field(
        0.2, title="Shutter Open Fraction"
    )
    cameras: bool = Field(False, title="Cameras", section="Show")
    clipGhosts: bool = Field(False, title="Clip Ghosts")
    deformers: bool = Field(False, title="Deformers")
    dimensions: bool = Field(False, title="Dimensions")
    dynamicConstraints: bool = Field(False, title="Dynamic Constraints")
    dynamics: bool = Field(False, title="Dynamics")
    fluids: bool = Field(False, title="Fluids")
    follicles: bool = Field(False, title="Follicles")
    greasePencils: bool = Field(False, title="Grease Pencils")
    grid: bool = Field(False, title="Grid")
    hairSystems: bool = Field(True, title="Hair Systems")
    handles: bool = Field(False, title="Handles")
    headsUpDisplay: bool = Field(False, title="HUD")
    ikHandles: bool = Field(False, title="IK Handles")
    imagePlane: bool = Field(True, title="Image Plane")
    joints: bool = Field(False, title="Joints")
    lights: bool = Field(False, title="Lights")
    locators: bool = Field(False, title="Locators")
    manipulators: bool = Field(False, title="Manipulators")
    motionTrails: bool = Field(False, title="Motion Trails")
    nCloths: bool = Field(False, title="nCloths")
    nParticles: bool = Field(False, title="nParticles")
    nRigids: bool = Field(False, title="nRigids")
    controlVertices: bool = Field(False, title="NURBS CVs")
    nurbsCurves: bool = Field(False, title="NURBS Curves")
    hulls: bool = Field(False, title="NURBS Hulls")
    nurbsSurfaces: bool = Field(False, title="NURBS Surfaces")
    particleInstancers: bool = Field(False, title="Particle Instancers")
    pivots: bool = Field(False, title="Pivots")
    planes: bool = Field(False, title="Planes")
    pluginShapes: bool = Field(False, title="Plugin Shapes")
    polymeshes: bool = Field(True, title="Polygons")
    strokes: bool = Field(False, title="Strokes")
    subdivSurfaces: bool = Field(False, title="Subdiv Surfaces")
    textures: bool = Field(False, title="Texture Placements")
    pluginObjects: list[PluginObjectsModel] = Field(
        default_factory=plugin_objects_default,
        title="Plugin Objects"
    )

    @validator("pluginObjects")
    def validate_unique_plugin_objects(cls, value):
        ensure_unique_names(value)
        return value


class CameraOptionsSetting(BaseSettingsModel):
    displayGateMask: bool = Field(False, title="Display Gate Mask")
    displayResolution: bool = Field(False, title="Display Resolution")
    displayFilmGate: bool = Field(False, title="Display Film Gate")
    displayFieldChart: bool = Field(False, title="Display Field Chart")
    displaySafeAction: bool = Field(False, title="Display Safe Action")
    displaySafeTitle: bool = Field(False, title="Display Safe Title")
    displayFilmPivot: bool = Field(False, title="Display Film Pivot")
    displayFilmOrigin: bool = Field(False, title="Display Film Origin")
    overscan: int = Field(1.0, title="Overscan")


class CapturePresetSetting(BaseSettingsModel):
    Codec: CodecSetting = Field(
        default_factory=CodecSetting,
        title="Codec",
        section="Codec")
    DisplayOptions: DisplayOptionsSetting = Field(
        default_factory=DisplayOptionsSetting,
        title="Display Options",
        section="Display Options")
    Generic: GenericSetting = Field(
        default_factory=GenericSetting,
        title="Generic",
        section="Generic")
    Renderer: RendererSetting = Field(
        default_factory=RendererSetting,
        title="Renderer",
        section="Renderer")
    Resolution: ResolutionSetting = Field(
        default_factory=ResolutionSetting,
        title="Resolution",
        section="Resolution")
    ViewportOptions: ViewportOptionsSetting = Field(
        default_factory=ViewportOptionsSetting,
        title="Viewport Options")
    CameraOptions: CameraOptionsSetting = Field(
        default_factory=CameraOptionsSetting,
        title="Camera Options")


class ProfilesModel(BaseSettingsModel):
    _layout = "expanded"
    task_types: list[str] = Field(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    task_names: list[str] = Field(default_factory=list, title="Task names")
    product_names: list[str] = Field(default_factory=list, title="Products names")
    capture_preset: CapturePresetSetting = Field(
        default_factory=CapturePresetSetting,
        title="Capture Preset"
    )


class ExtractPlayblastSetting(BaseSettingsModel):
    capture_preset: CapturePresetSetting = Field(
        default_factory=CapturePresetSetting,
        title="DEPRECATED! Please use \"Profiles\" below. Capture Preset"
    )
    profiles: list[ProfilesModel] = Field(
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
