"""Providing models and values for Maya Render Settings."""
from pydantic import Field

from ayon_server.settings import BaseSettingsModel


def aov_separators_enum():
    return [
        {"value": "dash", "label": "- (dash)"},
        {"value": "underscore", "label": "_ (underscore)"},
        {"value": "dot", "label": ". (dot)"}
    ]


def arnold_image_format_enum():
    """Return enumerator for Arnold output formats."""
    return [
        {"label": "jpeg", "value": "jpeg"},
        {"label": "png", "value": "png"},
        {"label": "deepexr", "value": "deep exr"},
        {"label": "tif", "value": "tif"},
        {"label": "exr", "value": "exr"},
        {"label": "maya", "value": "maya"},
        {"label": "mtoa_shaders", "value": "mtoa_shaders"}
      ]


def arnold_aov_list_enum():
    """Return enumerator for Arnold AOVs.

    Note: Key is value, Value in this case is Label. This
        was taken from v3 settings.
    """
    aovs = [
        {"empty": "< empty >"},
        {"ID": "ID"},
        {"N": "N"},
        {"P": "P"},
        {"Pref": "Pref"},
        {"RGBA": "RGBA"},
        {"Z": "Z"},
        {"albedo": "albedo"},
        {"background": "background"},
        {"coat": "coat"},
        {"coat_albedo": "coat_albedo"},
        {"coat_direct": "coat_direct"},
        {"coat_indirect": "coat_indirect"},
        {"cputime": "cputime"},
        {"crypto_asset": "crypto_asset"},
        {"crypto_material": "cypto_material"},
        {"crypto_object": "crypto_object"},
        {"diffuse": "diffuse"},
        {"diffuse_albedo": "diffuse_albedo"},
        {"diffuse_direct": "diffuse_direct"},
        {"diffuse_indirect": "diffuse_indirect"},
        {"direct": "direct"},
        {"emission": "emission"},
        {"highlight": "highlight"},
        {"indirect": "indirect"},
        {"motionvector": "motionvector"},
        {"opacity": "opacity"},
        {"raycount": "raycount"},
        {"rim_light": "rim_light"},
        {"shadow": "shadow"},
        {"shadow_diff": "shadow_diff"},
        {"shadow_mask": "shadow_mask"},
        {"shadow_matte": "shadow_matte"},
        {"sheen": "sheen"},
        {"sheen_albedo": "sheen_albedo"},
        {"sheen_direct": "sheen_direct"},
        {"sheen_indirect": "sheen_indirect"},
        {"specular": "specular"},
        {"specular_albedo": "specular_albedo"},
        {"specular_direct": "specular_direct"},
        {"specular_indirect": "specular_indirect"},
        {"sss": "sss"},
        {"sss_albedo": "sss_albedo"},
        {"sss_direct": "sss_direct"},
        {"sss_indirect": "sss_indirect"},
        {"transmission": "transmission"},
        {"transmission_albedo": "transmission_albedo"},
        {"transmission_direct": "transmission_direct"},
        {"transmission_indirect": "transmission_indirect"},
        {"volume": "volume"},
        {"volume_Z": "volume_Z"},
        {"volume_albedo": "volume_albedo"},
        {"volume_direct": "volume_direct"},
        {"volume_indirect": "volume_indirect"},
        {"volume_opacity": "volume_opacity"}
    ]

    return [{"label": list(aov.values())[0], "value": list(aov.keys())[0]} for aov in aovs]


def vray_image_output_enum():
    """Return output format for Vray enumerator."""
    return [
        {"label": "png", "value": "png"},
        {"label": "jpg", "value": "jpg"},
        {"label": "vrimg", "value": "vrimg"},
        {"label": "hdr", "value": "hdr"},
        {"label": "exr", "value": "exr"},
        {"label": "exr (multichannel)", "value": "exr (multichannel)"},
        {"label": "exr (deep)", "value": "exr (deep)"},
        {"label": "tga", "value": "tga"},
        {"label": "bmp", "value": "bmp"},
        {"label": "sgi", "value": "sgi"}
    ]


def vray_aov_list_enum():
    """Return enumerator for Vray AOVs.

        Note: Key is value, Value in this case is Label. This
            was taken from v3 settings.
        """
    aovs = [
        {"empty": "< empty >"},
        {"atmosphereChannel": "atmosphere"},
        {"backgroundChannel": "background"},
        {"bumpNormalsChannel": "bumpnormals"},
        {"causticsChannel": "caustics"},
        {"coatFilterChannel": "coat_filter"},
        {"coatGlossinessChannel": "coatGloss"},
        {"coatReflectionChannel": "coat_reflection"},
        {"vrayCoatChannel": "coat_specular"},
        {"CoverageChannel": "coverage"},
        {"cryptomatteChannel": "cryptomatte"},
        {"customColor": "custom_color"},
        {"drBucketChannel": "DR"},
        {"denoiserChannel": "denoiser"},
        {"diffuseChannel": "diffuse"},
        {"ExtraTexElement": "extraTex"},
        {"giChannel": "GI"},
        {"LightMixElement": "None"},
        {"lightingChannel": "lighting"},
        {"LightingAnalysisChannel": "LightingAnalysis"},
        {"materialIDChannel": "materialID"},
        {"MaterialSelectElement": "materialSelect"},
        {"matteShadowChannel": "matteShadow"},
        {"MultiMatteElement": "multimatte"},
        {"multimatteIDChannel": "multimatteID"},
        {"normalsChannel": "normals"},
        {"nodeIDChannel": "objectId"},
        {"objectSelectChannel": "objectSelect"},
        {"rawCoatFilterChannel": "raw_coat_filter"},
        {"rawCoatReflectionChannel": "raw_coat_reflection"},
        {"rawDiffuseFilterChannel": "rawDiffuseFilter"},
        {"rawGiChannel": "rawGI"},
        {"rawLightChannel": "rawLight"},
        {"rawReflectionChannel": "rawReflection"},
        {"rawReflectionFilterChannel": "rawReflectionFilter"},
        {"rawRefractionChannel": "rawRefraction"},
        {"rawRefractionFilterChannel": "rawRefractionFilter"},
        {"rawShadowChannel": "rawShadow"},
        {"rawSheenFilterChannel": "raw_sheen_filter"},
        {"rawSheenReflectionChannel": "raw_sheen_reflection"},
        {"rawTotalLightChannel": "rawTotalLight"},
        {"reflectIORChannel": "reflIOR"},
        {"reflectChannel": "reflect"},
        {"reflectionFilterChannel": "reflectionFilter"},
        {"reflectGlossinessChannel": "reflGloss"},
        {"refractChannel": "refract"},
        {"refractionFilterChannel": "refractionFilter"},
        {"refractGlossinessChannel": "refrGloss"},
        {"renderIDChannel": "renderId"},
        {"FastSSS2Channel": "SSS"},
        {"sampleRateChannel": "sampleRate"},
        {"samplerInfo": "samplerInfo"},
        {"selfIllumChannel": "selfIllum"},
        {"shadowChannel": "shadow"},
        {"sheenFilterChannel": "sheen_filter"},
        {"sheenGlossinessChannel": "sheenGloss"},
        {"sheenReflectionChannel": "sheen_reflection"},
        {"vraySheenChannel": "sheen_specular"},
        {"specularChannel": "specular"},
        {"Toon": "Toon"},
        {"toonLightingChannel": "toonLighting"},
        {"toonSpecularChannel": "toonSpecular"},
        {"totalLightChannel": "totalLight"},
        {"unclampedColorChannel": "unclampedColor"},
        {"VRScansPaintMaskChannel": "VRScansPaintMask"},
        {"VRScansZoneMaskChannel": "VRScansZoneMask"},
        {"velocityChannel": "velocity"},
        {"zdepthChannel": "zDepth"},
        {"LightSelectElement": "lightselect"}
    ]

    return [{"label": list(aov.values())[0], "value": list(aov.keys())[0]} for aov in aovs]


def redshift_engine_enum():
    """Get Redshift engine type enumerator."""
    return [
        {"value": "0", "label": "None"},
        {"value": "1", "label": "Photon Map"},
        {"value": "2", "label": "Irradiance Cache"},
        {"value": "3", "label": "Brute Force"}
    ]


def redshift_image_output_enum():
    """Return output format for Redshift enumerator."""
    return [
        {"value": "iff", "label": "Maya IFF"},
        {"value": "exr", "label": "OpenEXR"},
        {"value": "tif", "label": "TIFF"},
        {"value": "png", "label": "PNG"},
        {"value": "tga", "label": "Targa"},
        {"value": "jpg", "label": "JPEG"}
    ]


def redshift_aov_list_enum():
    """Return enumerator for Vray AOVs.

        Note: Key is value, Value in this case is Label. This
            was taken from v3 settings.
        """
    aovs = [
        {"empty": "< none >"},
        {"AO": "Ambient Occlusion"},
        {"Background": "Background"},
        {"Beauty": "Beauty"},
        {"BumpNormals": "Bump Normals"},
        {"Caustics": "Caustics"},
        {"CausticsRaw": "Caustics Raw"},
        {"Cryptomatte": "Cryptomatte"},
        {"Custom": "Custom"},
        {"Z": "Depth"},
        {"DiffuseFilter": "Diffuse Filter"},
        {"DiffuseLighting": "Diffuse Lighting"},
        {"DiffuseLightingRaw": "Diffuse Lighting Raw"},
        {"Emission": "Emission"},
        {"GI": "Global Illumination"},
        {"GIRaw": "Global Illumination Raw"},
        {"Matte": "Matte"},
        {"MotionVectors": "Ambient Occlusion"},
        {"N": "Normals"},
        {"ID": "ObjectID"},
        {"ObjectBumpNormal": "Object-Space Bump Normals"},
        {"ObjectPosition": "Object-Space Positions"},
        {"PuzzleMatte": "Puzzle Matte"},
        {"Reflections": "Reflections"},
        {"ReflectionsFilter": "Reflections Filter"},
        {"ReflectionsRaw": "Reflections Raw"},
        {"Refractions": "Refractions"},
        {"RefractionsFilter": "Refractions Filter"},
        {"RefractionsRaw": "Refractions Filter"},
        {"Shadows": "Shadows"},
        {"SpecularLighting": "Specular Lighting"},
        {"SSS": "Sub Surface Scatter"},
        {"SSSRaw": "Sub Surface Scatter Raw"},
        {"TotalDiffuseLightingRaw": "Total Diffuse Lighting Raw"},
        {"TotalTransLightingRaw": "Total Translucency Filter"},
        {"TransTint": "Translucency Filter"},
        {"TransGIRaw": "Translucency Lighting Raw"},
        {"VolumeFogEmission": "Volume Fog Emission"},
        {"VolumeFogTint": "Volume Fog Tint"},
        {"VolumeLighting": "Volume Lighting"},
        {"P": "World Position"}
    ]

    return [{"label": list(aov.values())[0], "value": list(aov.keys())[0]} for aov in aovs]


class AdditionalOptionsModel(BaseSettingsModel):
    """Additional Option"""
    _layout = "compact"

    attribute: str = Field("", title="Attribute name")
    value: str = Field("", title="Value")


class ArnoldSettingsModel(BaseSettingsModel):
    image_prefix: str = Field(title="Image prefix template")
    image_format: str = Field(
        enum_resolver=arnold_image_format_enum, title="Output Image Format")
    multilayer_exr: bool = Field(title="Multilayer (exr)")
    tiled: bool = Field(title="Tiled (tif, exr)")
    aov_list: list[str] = Field(default_factory=list, enum_resolver=arnold_aov_list_enum, title="AOVs to create")
    additional_options: list[AdditionalOptionsModel] = Field(
        default_factory=list, title="Additional Arnold Options",
        description=("Add additional options - put attribute and value, like AASamples"))


class VraySettingsModel(BaseSettingsModel):
    image_prefix: str = Field(title="Image prefix template")
    # engine was str because of JSON limitation (key must be string)
    engine: str = Field(
        enum_resolver=lambda: [
            {"label": "V-Ray", "value": "1"},
            {"label": "V-Ray GPU", "value": "2"}
        ],
        title="Production Engine"
    )
    image_format: str = Field(enum_resolver=vray_image_output_enum, title="Output Image Format")
    aov_list: list[str] = Field(default_factory=list, enum_resolver=vray_aov_list_enum, title="AOVs to create")
    additional_options: list[AdditionalOptionsModel] = Field(
        default_factory=list, title="Additional Vray Options",
        description=("Add additional options - put attribute and value, like aaFilterSize"))


class RedshiftSettingsModel(BaseSettingsModel):
    image_prefix: str = Field(title="Image prefix template")
    # both engines are using the same enumerator, both were originally str because of JSON limitation.
    primary_gi_engine: str = Field(enum_resolver=redshift_engine_enum, title="Primary GI Engine")
    secondary_gi_engine: str = Field(enum_resolver=redshift_engine_enum, title="Secondary GI Engine")
    image_format: str = Field(enum_resolver=redshift_image_output_enum, title="Output Image Format")
    multilayer_exr: bool = Field(title="Multilayer (exr)")
    force_combine: bool = Field(title="Force combine beauty and AOVs")
    aov_list: list[str] = Field(default_factory=list, enum_resolver=redshift_aov_list_enum, title="AOVs to create")
    additional_options: list[AdditionalOptionsModel] = Field(
        default_factory=list, title="Additional Vray Options",
        description=("Add additional options - put attribute and value, like reflectionMaxTraceDepth"))


def renderman_display_filters():
    return [
        "PxrBackgroundDisplayFilter",
        "PxrCopyAOVDisplayFilter",
        "PxrEdgeDetect",
        "PxrFilmicTonemapperDisplayFilter",
        "PxrGradeDisplayFilter",
        "PxrHalfBufferErrorFilter",
        "PxrImageDisplayFilter",
        "PxrLightSaturation",
        "PxrShadowDisplayFilter",
        "PxrStylizedHatching",
        "PxrStylizedLines",
        "PxrStylizedToon",
        "PxrWhitePointDisplayFilter"
    ]


def renderman_sample_filters_enum():
    return [
        "PxrBackgroundSampleFilter",
        "PxrCopyAOVSampleFilter",
        "PxrCryptomatte",
        "PxrFilmicTonemapperSampleFilter",
        "PxrGradeSampleFilter",
        "PxrShadowFilter",
        "PxrWatermarkFilter",
        "PxrWhitePointSampleFilter"
    ]


class RendermanSettingsModel(BaseSettingsModel):
    image_prefix: str = Field("", title="Image prefix template")
    image_dir: str = Field("", title="Image Output Directory")
    display_filters: list[str] = Field(
        default_factory=list,
        title="Display Filters",
        enum_resolver=renderman_display_filters
    )
    imageDisplay_dir: str = Field("", title="Image Display Filter Directory")
    sample_filters: list[str] = Field(
        default_factory=list,
        title="Sample Filters",
        enum_resolver=renderman_sample_filters_enum
    )
    cryptomatte_dir: str = Field("", title="Cryptomatte Output Directory")
    watermark_dir: str = Field("", title="Watermark Filter Directory")
    additional_options: list[AdditionalOptionsModel] = Field(
        default_factory=list,
        title="Additional Renderer Options"
    )


class RenderSettingsModel(BaseSettingsModel):
    apply_render_settings: bool = Field(title="Apply Render Settings on creation")
    default_render_image_folder: str = Field(title="Default render image folder")
    enable_all_lights: bool = Field(title="Include all lights in Render Setup Layers by default")
    aov_separator: str = Field(
        "underscore",
        title="AOV Separator character",
        enum_resolver=aov_separators_enum
    )
    reset_current_frame: bool = Field(title="Reset Current Frame")
    remove_aovs: bool = Field(title="Remove existing AOVs")
    arnold_renderer: ArnoldSettingsModel = Field(
        default_factory=ArnoldSettingsModel, title="Arnold Renderer")
    vray_renderer: VraySettingsModel = Field(
        default_factory=VraySettingsModel, title="Vray Renderer")
    redshift_renderer: RedshiftSettingsModel = Field(
        default_factory=RedshiftSettingsModel, title="Redshift Renderer")
    renderman_renderer: RendermanSettingsModel = Field(
        default_factory=RendermanSettingsModel, title="Renderman Renderer")


DEFAULT_RENDER_SETTINGS = {
    "apply_render_settings": True,
    "default_render_image_folder": "renders/maya",
    "enable_all_lights": True,
    "aov_separator": "underscore",
    "reset_current_frame": False,
    "remove_aovs": False,
    "arnold_renderer": {
        "image_prefix": "<Scene>/<RenderLayer>/<RenderLayer>_<RenderPass>",
        "image_format": "exr",
        "multilayer_exr": True,
        "tiled": True,
        "aov_list": [],
        "additional_options": []
    },
    "vray_renderer": {
        "image_prefix": "<scene>/<Layer>/<Layer>",
        "engine": "1",
        "image_format": "exr",
        "aov_list": [],
        "additional_options": []
    },
    "redshift_renderer": {
        "image_prefix": "<Scene>/<RenderLayer>/<RenderLayer>",
        "primary_gi_engine": "0",
        "secondary_gi_engine": "0",
        "image_format": "exr",
        "multilayer_exr": True,
        "force_combine": True,
        "aov_list": [],
        "additional_options": []
    },
    "renderman_renderer": {
        "image_prefix": "<layer>{aov_separator}<aov>.<f4>.<ext>",
        "image_dir": "<scene>/<layer>",
        "display_filters": [],
        "imageDisplay_dir": "<imagedir>/<layer>{aov_separator}imageDisplayFilter.<f4>.<ext>",
        "sample_filters": [],
        "cryptomatte_dir": "<imagedir>/<layer>{aov_separator}cryptomatte.<f4>.<ext>",
        "watermark_dir": "<imagedir>/<layer>{aov_separator}watermarkFilter.<f4>.<ext>",
        "additional_options": []
    }
}
