"""Providing models and values for Maya Render Settings."""
from ayon_server.settings import BaseSettingsModel, SettingsField


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
    return [
        {"value": "empty", "label": "< empty >"},
        {"value": "ID", "label": "ID"},
        {"value": "N", "label": "N"},
        {"value": "P", "label": "P"},
        {"value": "Pref", "label": "Pref"},
        {"value": "RGBA", "label": "RGBA"},
        {"value": "Z", "label": "Z"},
        {"value": "albedo", "label": "albedo"},
        {"value": "background", "label": "background"},
        {"value": "coat", "label": "coat"},
        {"value": "coat_albedo", "label": "coat_albedo"},
        {"value": "coat_direct", "label": "coat_direct"},
        {"value": "coat_indirect", "label": "coat_indirect"},
        {"value": "cputime", "label": "cputime"},
        {"value": "crypto_asset", "label": "crypto_asset"},
        {"value": "crypto_material", "label": "cypto_material"},
        {"value": "crypto_object", "label": "crypto_object"},
        {"value": "diffuse", "label": "diffuse"},
        {"value": "diffuse_albedo", "label": "diffuse_albedo"},
        {"value": "diffuse_direct", "label": "diffuse_direct"},
        {"value": "diffuse_indirect", "label": "diffuse_indirect"},
        {"value": "direct", "label": "direct"},
        {"value": "emission", "label": "emission"},
        {"value": "highlight", "label": "highlight"},
        {"value": "indirect", "label": "indirect"},
        {"value": "motionvector", "label": "motionvector"},
        {"value": "opacity", "label": "opacity"},
        {"value": "raycount", "label": "raycount"},
        {"value": "rim_light", "label": "rim_light"},
        {"value": "shadow", "label": "shadow"},
        {"value": "shadow_diff", "label": "shadow_diff"},
        {"value": "shadow_mask", "label": "shadow_mask"},
        {"value": "shadow_matte", "label": "shadow_matte"},
        {"value": "sheen", "label": "sheen"},
        {"value": "sheen_albedo", "label": "sheen_albedo"},
        {"value": "sheen_direct", "label": "sheen_direct"},
        {"value": "sheen_indirect", "label": "sheen_indirect"},
        {"value": "specular", "label": "specular"},
        {"value": "specular_albedo", "label": "specular_albedo"},
        {"value": "specular_direct", "label": "specular_direct"},
        {"value": "specular_indirect", "label": "specular_indirect"},
        {"value": "sss", "label": "sss"},
        {"value": "sss_albedo", "label": "sss_albedo"},
        {"value": "sss_direct", "label": "sss_direct"},
        {"value": "sss_indirect", "label": "sss_indirect"},
        {"value": "transmission", "label": "transmission"},
        {"value": "transmission_albedo", "label": "transmission_albedo"},
        {"value": "transmission_direct", "label": "transmission_direct"},
        {"value": "transmission_indirect", "label": "transmission_indirect"},
        {"value": "volume", "label": "volume"},
        {"value": "volume_Z", "label": "volume_Z"},
        {"value": "volume_albedo", "label": "volume_albedo"},
        {"value": "volume_direct", "label": "volume_direct"},
        {"value": "volume_indirect", "label": "volume_indirect"},
        {"value": "volume_opacity", "label": "volume_opacity"},
    ]


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

    return [
        {"value": "empty", "label": "< empty >"},
        {"value": "atmosphereChannel", "label": "atmosphere"},
        {"value": "backgroundChannel", "label": "background"},
        {"value": "bumpNormalsChannel", "label": "bumpnormals"},
        {"value": "causticsChannel", "label": "caustics"},
        {"value": "coatFilterChannel", "label": "coat_filter"},
        {"value": "coatGlossinessChannel", "label": "coatGloss"},
        {"value": "coatReflectionChannel", "label": "coat_reflection"},
        {"value": "vrayCoatChannel", "label": "coat_specular"},
        {"value": "CoverageChannel", "label": "coverage"},
        {"value": "cryptomatteChannel", "label": "cryptomatte"},
        {"value": "customColor", "label": "custom_color"},
        {"value": "drBucketChannel", "label": "DR"},
        {"value": "denoiserChannel", "label": "denoiser"},
        {"value": "diffuseChannel", "label": "diffuse"},
        {"value": "ExtraTexElement", "label": "extraTex"},
        {"value": "giChannel", "label": "GI"},
        {"value": "LightMixElement", "label": "None"},
        {"value": "lightingChannel", "label": "lighting"},
        {"value": "LightingAnalysisChannel", "label": "LightingAnalysis"},
        {"value": "materialIDChannel", "label": "materialID"},
        {"value": "MaterialSelectElement", "label": "materialSelect"},
        {"value": "matteShadowChannel", "label": "matteShadow"},
        {"value": "MultiMatteElement", "label": "multimatte"},
        {"value": "multimatteIDChannel", "label": "multimatteID"},
        {"value": "normalsChannel", "label": "normals"},
        {"value": "nodeIDChannel", "label": "objectId"},
        {"value": "objectSelectChannel", "label": "objectSelect"},
        {"value": "rawCoatFilterChannel", "label": "raw_coat_filter"},
        {"value": "rawCoatReflectionChannel", "label": "raw_coat_reflection"},
        {"value": "rawDiffuseFilterChannel", "label": "rawDiffuseFilter"},
        {"value": "rawGiChannel", "label": "rawGI"},
        {"value": "rawLightChannel", "label": "rawLight"},
        {"value": "rawReflectionChannel", "label": "rawReflection"},
        {
            "value": "rawReflectionFilterChannel",
            "label": "rawReflectionFilter"
        },
        {"value": "rawRefractionChannel", "label": "rawRefraction"},
        {
            "value": "rawRefractionFilterChannel",
            "label": "rawRefractionFilter"
        },
        {"value": "rawShadowChannel", "label": "rawShadow"},
        {"value": "rawSheenFilterChannel", "label": "raw_sheen_filter"},
        {
            "value": "rawSheenReflectionChannel",
            "label": "raw_sheen_reflection"
        },
        {"value": "rawTotalLightChannel", "label": "rawTotalLight"},
        {"value": "reflectIORChannel", "label": "reflIOR"},
        {"value": "reflectChannel", "label": "reflect"},
        {"value": "reflectionFilterChannel", "label": "reflectionFilter"},
        {"value": "reflectGlossinessChannel", "label": "reflGloss"},
        {"value": "refractChannel", "label": "refract"},
        {"value": "refractionFilterChannel", "label": "refractionFilter"},
        {"value": "refractGlossinessChannel", "label": "refrGloss"},
        {"value": "renderIDChannel", "label": "renderId"},
        {"value": "FastSSS2Channel", "label": "SSS"},
        {"value": "sampleRateChannel", "label": "sampleRate"},
        {"value": "samplerInfo", "label": "samplerInfo"},
        {"value": "selfIllumChannel", "label": "selfIllum"},
        {"value": "shadowChannel", "label": "shadow"},
        {"value": "sheenFilterChannel", "label": "sheen_filter"},
        {"value": "sheenGlossinessChannel", "label": "sheenGloss"},
        {"value": "sheenReflectionChannel", "label": "sheen_reflection"},
        {"value": "vraySheenChannel", "label": "sheen_specular"},
        {"value": "specularChannel", "label": "specular"},
        {"value": "Toon", "label": "Toon"},
        {"value": "toonLightingChannel", "label": "toonLighting"},
        {"value": "toonSpecularChannel", "label": "toonSpecular"},
        {"value": "totalLightChannel", "label": "totalLight"},
        {"value": "unclampedColorChannel", "label": "unclampedColor"},
        {"value": "VRScansPaintMaskChannel", "label": "VRScansPaintMask"},
        {"value": "VRScansZoneMaskChannel", "label": "VRScansZoneMask"},
        {"value": "velocityChannel", "label": "velocity"},
        {"value": "zdepthChannel", "label": "zDepth"},
        {"value": "LightSelectElement", "label": "lightselect"},
    ]


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
    return [
        {"value": "empty", "label": "< none >"},
        {"value": "AO", "label": "Ambient Occlusion"},
        {"value": "Background", "label": "Background"},
        {"value": "Beauty", "label": "Beauty"},
        {"value": "BumpNormals", "label": "Bump Normals"},
        {"value": "Caustics", "label": "Caustics"},
        {"value": "CausticsRaw", "label": "Caustics Raw"},
        {"value": "Cryptomatte", "label": "Cryptomatte"},
        {"value": "Custom", "label": "Custom"},
        {"value": "Z", "label": "Depth"},
        {"value": "DiffuseFilter", "label": "Diffuse Filter"},
        {"value": "DiffuseLighting", "label": "Diffuse Lighting"},
        {"value": "DiffuseLightingRaw", "label": "Diffuse Lighting Raw"},
        {"value": "Emission", "label": "Emission"},
        {"value": "GI", "label": "Global Illumination"},
        {"value": "GIRaw", "label": "Global Illumination Raw"},
        {"value": "Matte", "label": "Matte"},
        {"value": "MotionVectors", "label": "Ambient Occlusion"},
        {"value": "N", "label": "Normals"},
        {"value": "ID", "label": "ObjectID"},
        {"value": "ObjectBumpNormal", "label": "Object-Space Bump Normals"},
        {"value": "ObjectPosition", "label": "Object-Space Positions"},
        {"value": "PuzzleMatte", "label": "Puzzle Matte"},
        {"value": "Reflections", "label": "Reflections"},
        {"value": "ReflectionsFilter", "label": "Reflections Filter"},
        {"value": "ReflectionsRaw", "label": "Reflections Raw"},
        {"value": "Refractions", "label": "Refractions"},
        {"value": "RefractionsFilter", "label": "Refractions Filter"},
        {"value": "RefractionsRaw", "label": "Refractions Filter"},
        {"value": "Shadows", "label": "Shadows"},
        {"value": "SpecularLighting", "label": "Specular Lighting"},
        {"value": "SSS", "label": "Sub Surface Scatter"},
        {"value": "SSSRaw", "label": "Sub Surface Scatter Raw"},
        {
            "value": "TotalDiffuseLightingRaw",
            "label": "Total Diffuse Lighting Raw"
        },
        {
            "value": "TotalTransLightingRaw",
            "label": "Total Translucency Filter"
        },
        {"value": "TransTint", "label": "Translucency Filter"},
        {"value": "TransGIRaw", "label": "Translucency Lighting Raw"},
        {"value": "VolumeFogEmission", "label": "Volume Fog Emission"},
        {"value": "VolumeFogTint", "label": "Volume Fog Tint"},
        {"value": "VolumeLighting", "label": "Volume Lighting"},
        {"value": "P", "label": "World Position"},
    ]


class AdditionalOptionsModel(BaseSettingsModel):
    """Additional Option"""
    _layout = "compact"

    attribute: str = SettingsField("", title="Attribute name")
    value: str = SettingsField("", title="Value")


class ArnoldSettingsModel(BaseSettingsModel):
    image_prefix: str = SettingsField(title="Image prefix template")
    image_format: str = SettingsField(
        enum_resolver=arnold_image_format_enum, title="Output Image Format")
    multilayer_exr: bool = SettingsField(title="Multilayer (exr)")
    tiled: bool = SettingsField(title="Tiled (tif, exr)")
    aov_list: list[str] = SettingsField(
        default_factory=list,
        enum_resolver=arnold_aov_list_enum,
        title="AOVs to create"
    )
    additional_options: list[AdditionalOptionsModel] = SettingsField(
        default_factory=list,
        title="Additional Arnold Options",
        description=(
            "Add additional options - put attribute and value, like AASamples"
            " and 4"
        )
    )


class VraySettingsModel(BaseSettingsModel):
    image_prefix: str = SettingsField(title="Image prefix template")
    # engine was str because of JSON limitation (key must be string)
    engine: str = SettingsField(
        enum_resolver=lambda: [
            {"label": "V-Ray", "value": "1"},
            {"label": "V-Ray GPU", "value": "2"}
        ],
        title="Production Engine"
    )
    image_format: str = SettingsField(
        enum_resolver=vray_image_output_enum,
        title="Output Image Format"
    )
    aov_list: list[str] = SettingsField(
        default_factory=list,
        enum_resolver=vray_aov_list_enum,
        title="AOVs to create"
    )
    additional_options: list[AdditionalOptionsModel] = SettingsField(
        default_factory=list,
        title="Additional Vray Options",
        description=(
            "Add additional options - put attribute and value, like "
            "aaFilterSize and 1.5"
        )
    )


class RedshiftSettingsModel(BaseSettingsModel):
    image_prefix: str = SettingsField(title="Image prefix template")
    # both engines are using the same enumerator,
    #   both were originally str because of JSON limitation.
    primary_gi_engine: str = SettingsField(
        enum_resolver=redshift_engine_enum,
        title="Primary GI Engine"
    )
    secondary_gi_engine: str = SettingsField(
        enum_resolver=redshift_engine_enum,
        title="Secondary GI Engine"
    )
    image_format: str = SettingsField(
        enum_resolver=redshift_image_output_enum,
        title="Output Image Format"
    )
    multilayer_exr: bool = SettingsField(title="Multilayer (exr)")
    force_combine: bool = SettingsField(title="Force combine beauty and AOVs")
    aov_list: list[str] = SettingsField(
        default_factory=list,
        enum_resolver=redshift_aov_list_enum,
        title="AOVs to create"
    )
    additional_options: list[AdditionalOptionsModel] = SettingsField(
        default_factory=list,
        title="Additional Vray Options",
        description=(
            "Add additional options - put attribute and value, like "
            "reflectionMaxTraceDepth and 3"
        )
    )


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
    image_prefix: str = SettingsField(
        "", title="Image prefix template")
    image_dir: str = SettingsField(
        "", title="Image Output Directory")
    display_filters: list[str] = SettingsField(
        default_factory=list,
        title="Display Filters",
        enum_resolver=renderman_display_filters
    )
    imageDisplay_dir: str = SettingsField(
        "", title="Image Display Filter Directory")
    sample_filters: list[str] = SettingsField(
        default_factory=list,
        title="Sample Filters",
        enum_resolver=renderman_sample_filters_enum
    )
    cryptomatte_dir: str = SettingsField(
        "", title="Cryptomatte Output Directory")
    watermark_dir: str = SettingsField(
        "", title="Watermark Filter Directory")
    additional_options: list[AdditionalOptionsModel] = SettingsField(
        default_factory=list,
        title="Additional Renderer Options"
    )


class RenderSettingsModel(BaseSettingsModel):
    apply_render_settings: bool = SettingsField(
        title="Apply Render Settings on creation"
    )
    default_render_image_folder: str = SettingsField(
        title="Default render image folder"
    )
    enable_all_lights: bool = SettingsField(
        title="Include all lights in Render Setup Layers by default"
    )
    aov_separator: str = SettingsField(
        "underscore",
        title="AOV Separator character",
        enum_resolver=aov_separators_enum
    )
    reset_current_frame: bool = SettingsField(
        title="Reset Current Frame")
    remove_aovs: bool = SettingsField(
        title="Remove existing AOVs")
    arnold_renderer: ArnoldSettingsModel = SettingsField(
        default_factory=ArnoldSettingsModel,
        title="Arnold Renderer")
    vray_renderer: VraySettingsModel = SettingsField(
        default_factory=VraySettingsModel,
        title="Vray Renderer")
    redshift_renderer: RedshiftSettingsModel = SettingsField(
        default_factory=RedshiftSettingsModel,
        title="Redshift Renderer")
    renderman_renderer: RendermanSettingsModel = SettingsField(
        default_factory=RendermanSettingsModel,
        title="Renderman Renderer")


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
