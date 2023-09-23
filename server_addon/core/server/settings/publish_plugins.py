from pydantic import Field, validator

from ayon_server.settings import (
    BaseSettingsModel,
    MultiplatformPathModel,
    normalize_name,
    ensure_unique_names,
    task_types_enum,
)

from ayon_server.types import ColorRGBA_uint8


class ValidateBaseModel(BaseSettingsModel):
    _isGroup = True
    enabled: bool = Field(True)
    optional: bool = Field(True, title="Optional")
    active: bool = Field(True, title="Active")


class CollectAnatomyInstanceDataModel(BaseSettingsModel):
    _isGroup = True
    follow_workfile_version: bool = Field(
        True, title="Collect Anatomy Instance Data"
    )


class CollectAudioModel(BaseSettingsModel):
    _isGroup = True
    enabled: bool = Field(True)
    audio_product_name: str = Field(
        "", title="Name of audio variant"
    )


class CollectSceneVersionModel(BaseSettingsModel):
    _isGroup = True
    hosts: list[str] = Field(
        default_factory=list,
        title="Host names"
    )
    skip_hosts_headless_publish: list[str] = Field(
        default_factory=list,
        title="Skip for host if headless publish"
    )


class CollectCommentPIModel(BaseSettingsModel):
    enabled: bool = Field(True)
    families: list[str] = Field(default_factory=list, title="Families")


class CollectFramesFixDefModel(BaseSettingsModel):
    enabled: bool = Field(True)
    rewrite_version_enable: bool = Field(
        True,
        title="Show 'Rewrite latest version' toggle"
    )


class ValidateIntentProfile(BaseSettingsModel):
    _layout = "expanded"
    hosts: list[str] = Field(default_factory=list, title="Host names")
    task_types: list[str] = Field(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    tasks: list[str] = Field(default_factory=list, title="Task names")
    # TODO This was 'validate' in v3
    validate_intent: bool = Field(True, title="Validate")


class ValidateIntentModel(BaseSettingsModel):
    """Validate if Publishing intent was selected.

    It is possible to disable validation for specific publishing context
    with profiles.
    """

    _isGroup = True
    enabled: bool = Field(False)
    profiles: list[ValidateIntentProfile] = Field(default_factory=list)


class ExtractThumbnailFFmpegModel(BaseSettingsModel):
    _layout = "expanded"
    input: list[str] = Field(
        default_factory=list,
        title="FFmpeg input arguments"
    )
    output: list[str] = Field(
        default_factory=list,
        title="FFmpeg input arguments"
    )


class ExtractThumbnailModel(BaseSettingsModel):
    _isGroup = True
    enabled: bool = Field(True)
    ffmpeg_args: ExtractThumbnailFFmpegModel = Field(
        default_factory=ExtractThumbnailFFmpegModel
    )


def _extract_oiio_transcoding_type():
    return [
        {"value": "colorspace", "label": "Use Colorspace"},
        {"value": "display", "label": "Use Display&View"}
    ]


class OIIOToolArgumentsModel(BaseSettingsModel):
    additional_command_args: list[str] = Field(
        default_factory=list, title="Arguments")


class ExtractOIIOTranscodeOutputModel(BaseSettingsModel):
    _layout = "expanded"
    name: str = Field("", title="Name")
    extension: str = Field("", title="Extension")
    transcoding_type: str = Field(
        "colorspace",
        title="Transcoding type",
        enum_resolver=_extract_oiio_transcoding_type
    )
    colorspace: str = Field("", title="Colorspace")
    display: str = Field("", title="Display")
    view: str = Field("", title="View")
    oiiotool_args: OIIOToolArgumentsModel = Field(
        default_factory=OIIOToolArgumentsModel,
        title="OIIOtool arguments")

    tags: list[str] = Field(default_factory=list, title="Tags")
    custom_tags: list[str] = Field(default_factory=list, title="Custom Tags")


class ExtractOIIOTranscodeProfileModel(BaseSettingsModel):
    product_types: list[str] = Field(
        default_factory=list,
        title="Product types"
    )
    hosts: list[str] = Field(
        default_factory=list,
        title="Host names"
    )
    task_types: list[str] = Field(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    task_names: list[str] = Field(
        default_factory=list,
        title="Task names"
    )
    product_names: list[str] = Field(
        default_factory=list,
        title="Product names"
    )
    delete_original: bool = Field(
        True,
        title="Delete Original Representation"
    )
    outputs: list[ExtractOIIOTranscodeOutputModel] = Field(
        default_factory=list,
        title="Output Definitions",
    )

    @validator("outputs")
    def validate_unique_outputs(cls, value):
        ensure_unique_names(value)
        return value


class ExtractOIIOTranscodeModel(BaseSettingsModel):
    enabled: bool = Field(True)
    profiles: list[ExtractOIIOTranscodeProfileModel] = Field(
        default_factory=list, title="Profiles"
    )


# --- [START] Extract Review ---
class ExtractReviewFFmpegModel(BaseSettingsModel):
    video_filters: list[str] = Field(
        default_factory=list,
        title="Video filters"
    )
    audio_filters: list[str] = Field(
        default_factory=list,
        title="Audio filters"
    )
    input: list[str] = Field(
        default_factory=list,
        title="Input arguments"
    )
    output: list[str] = Field(
        default_factory=list,
        title="Output arguments"
    )


def extract_review_filter_enum():
    return [
        {
            "value": "everytime",
            "label": "Always"
        },
        {
            "value": "single_frame",
            "label": "Only if input has 1 image frame"
        },
        {
            "value": "multi_frame",
            "label": "Only if input is video or sequence of frames"
        }
    ]


class ExtractReviewFilterModel(BaseSettingsModel):
    families: list[str] = Field(default_factory=list, title="Families")
    product_names: list[str] = Field(
        default_factory=list, title="Product names")
    custom_tags: list[str] = Field(default_factory=list, title="Custom Tags")
    single_frame_filter: str = Field(
        "everytime",
        description=(
            "Use output <b>always</b> / only if input <b>is 1 frame</b>"
            " image / only if has <b>2+ frames</b> or <b>is video</b>"
        ),
        enum_resolver=extract_review_filter_enum
    )


class ExtractReviewLetterBox(BaseSettingsModel):
    enabled: bool = Field(True)
    ratio: float = Field(
        0.0,
        title="Ratio",
        ge=0.0,
        le=10000.0
    )
    fill_color: ColorRGBA_uint8 = Field(
        (0, 0, 0, 0.0),
        title="Fill Color"
    )
    line_thickness: int = Field(
        0,
        title="Line Thickness",
        ge=0,
        le=1000
    )
    line_color: ColorRGBA_uint8 = Field(
        (0, 0, 0, 0.0),
        title="Line Color"
    )


class ExtractReviewOutputDefModel(BaseSettingsModel):
    _layout = "expanded"
    name: str = Field("", title="Name")
    ext: str = Field("", title="Output extension")
    # TODO use some different source of tags
    tags: list[str] = Field(default_factory=list, title="Tags")
    burnins: list[str] = Field(
        default_factory=list, title="Link to a burnin by name"
    )
    ffmpeg_args: ExtractReviewFFmpegModel = Field(
        default_factory=ExtractReviewFFmpegModel,
        title="FFmpeg arguments"
    )
    filter: ExtractReviewFilterModel = Field(
        default_factory=ExtractReviewFilterModel,
        title="Additional output filtering"
    )
    overscan_crop: str = Field(
        "",
        title="Overscan crop",
        description=(
            "Crop input overscan. See the documentation for more information."
        )
    )
    overscan_color: ColorRGBA_uint8 = Field(
        (0, 0, 0, 0.0),
        title="Overscan color",
        description=(
            "Overscan color is used when input aspect ratio is not"
            " same as output aspect ratio."
        )
    )
    width: int = Field(
        0,
        ge=0,
        le=100000,
        title="Output width",
        description=(
            "Width and Height must be both set to higher"
            " value than 0 else source resolution is used."
        )
    )
    height: int = Field(
        0,
        title="Output height",
        ge=0,
        le=100000,
    )
    scale_pixel_aspect: bool = Field(
        True,
        title="Scale pixel aspect",
        description=(
            "Rescale input when it's pixel aspect ratio is not 1."
            " Usefull for anamorph reviews."
        )
    )
    bg_color: ColorRGBA_uint8 = Field(
        (0, 0, 0, 0.0),
        description=(
            "Background color is used only when input have transparency"
            " and Alpha is higher than 0."
        ),
        title="Background color",
    )
    letter_box: ExtractReviewLetterBox = Field(
        default_factory=ExtractReviewLetterBox,
        title="Letter Box"
    )

    @validator("name")
    def validate_name(cls, value):
        """Ensure name does not contain weird characters"""
        return normalize_name(value)


class ExtractReviewProfileModel(BaseSettingsModel):
    _layout = "expanded"
    product_types: list[str] = Field(
        default_factory=list, title="Product types"
    )
    # TODO use hosts enum
    hosts: list[str] = Field(
        default_factory=list, title="Host names"
    )
    outputs: list[ExtractReviewOutputDefModel] = Field(
        default_factory=list, title="Output Definitions"
    )

    @validator("outputs")
    def validate_unique_outputs(cls, value):
        ensure_unique_names(value)
        return value


class ExtractReviewModel(BaseSettingsModel):
    _isGroup = True
    enabled: bool = Field(True)
    profiles: list[ExtractReviewProfileModel] = Field(
        default_factory=list,
        title="Profiles"
    )
# --- [END] Extract Review ---


# --- [Start] Extract Burnin ---
class ExtractBurninOptionsModel(BaseSettingsModel):
    font_size: int = Field(0, ge=0, title="Font size")
    font_color: ColorRGBA_uint8 = Field(
        (255, 255, 255, 1.0),
        title="Font color"
    )
    bg_color: ColorRGBA_uint8 = Field(
        (0, 0, 0, 1.0),
        title="Background color"
    )
    x_offset: int = Field(0, title="X Offset")
    y_offset: int = Field(0, title="Y Offset")
    bg_padding: int = Field(0, title="Padding around text")
    font_filepath: MultiplatformPathModel = Field(
        default_factory=MultiplatformPathModel,
        title="Font file path"
    )


class ExtractBurninDefFilter(BaseSettingsModel):
    families: list[str] = Field(
        default_factory=list,
        title="Families"
    )
    tags: list[str] = Field(
        default_factory=list,
        title="Tags"
    )


class ExtractBurninDef(BaseSettingsModel):
    _isGroup = True
    _layout = "expanded"
    name: str = Field("")
    TOP_LEFT: str = Field("", topic="Top Left")
    TOP_CENTERED: str = Field("", topic="Top Centered")
    TOP_RIGHT: str = Field("", topic="Top Right")
    BOTTOM_LEFT: str = Field("", topic="Bottom Left")
    BOTTOM_CENTERED: str = Field("", topic="Bottom Centered")
    BOTTOM_RIGHT: str = Field("", topic="Bottom Right")
    filter: ExtractBurninDefFilter = Field(
        default_factory=ExtractBurninDefFilter,
        title="Additional filtering"
    )

    @validator("name")
    def validate_name(cls, value):
        """Ensure name does not contain weird characters"""
        return normalize_name(value)


class ExtractBurninProfile(BaseSettingsModel):
    _layout = "expanded"
    product_types: list[str] = Field(
        default_factory=list,
        title="Produt types"
    )
    hosts: list[str] = Field(
        default_factory=list,
        title="Host names"
    )
    task_types: list[str] = Field(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    task_names: list[str] = Field(
        default_factory=list,
        title="Task names"
    )
    product_names: list[str] = Field(
        default_factory=list,
        title="Product names"
    )
    burnins: list[ExtractBurninDef] = Field(
        default_factory=list,
        title="Burnins"
    )

    @validator("burnins")
    def validate_unique_outputs(cls, value):
        ensure_unique_names(value)

        return value


class ExtractBurninModel(BaseSettingsModel):
    _isGroup = True
    enabled: bool = Field(True)
    options: ExtractBurninOptionsModel = Field(
        default_factory=ExtractBurninOptionsModel,
        title="Burnin formatting options"
    )
    profiles: list[ExtractBurninProfile] = Field(
        default_factory=list,
        title="Profiles"
    )
# --- [END] Extract Burnin ---


class PreIntegrateThumbnailsProfile(BaseSettingsModel):
    _isGroup = True
    product_types: list[str] = Field(
        default_factory=list,
        title="Product types",
    )
    hosts: list[str] = Field(
        default_factory=list,
        title="Hosts",
    )
    task_types: list[str] = Field(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    product_names: list[str] = Field(
        default_factory=list,
        title="Product names",
    )
    integrate_thumbnail: bool = Field(True)


class PreIntegrateThumbnailsModel(BaseSettingsModel):
    """Explicitly set if Thumbnail representation should be integrated.

    If no matching profile set, existing state from Host implementation
    is kept.
    """

    _isGroup = True
    enabled: bool = Field(True)
    integrate_profiles: list[PreIntegrateThumbnailsProfile] = Field(
        default_factory=list,
        title="Integrate profiles"
    )


class IntegrateProductGroupProfile(BaseSettingsModel):
    product_types: list[str] = Field(
        default_factory=list,
        title="Product types"
    )
    hosts: list[str] = Field(default_factory=list, title="Hosts")
    task_types: list[str] = Field(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    tasks: list[str] = Field(default_factory=list, title="Task names")
    template: str = Field("", title="Template")


class IntegrateProductGroupModel(BaseSettingsModel):
    """Group published products by filtering logic.

    Set all published instances as a part of specific group named according
     to 'Template'.

    Implemented all variants of placeholders '{task}', '{product[type]}',
    '{host}', '{product[name]}', '{renderlayer}'.
    """

    _isGroup = True
    product_grouping_profiles: list[IntegrateProductGroupProfile] = Field(
        default_factory=list,
        title="Product group profiles"
    )


class IntegrateANProductGroupProfileModel(BaseSettingsModel):
    product_types: list[str] = Field(
        default_factory=list,
        title="Product types"
    )
    hosts: list[str] = Field(
        default_factory=list,
        title="Hosts"
    )
    task_types: list[str] = Field(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    tasks: list[str] = Field(
        default_factory=list,
        title="Task names"
    )
    template: str = Field("", title="Template")


class IntegrateANTemplateNameProfileModel(BaseSettingsModel):
    product_types: list[str] = Field(
        default_factory=list,
        title="Product types"
    )
    hosts: list[str] = Field(
        default_factory=list,
        title="Hosts"
    )
    task_types: list[str] = Field(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    tasks: list[str] = Field(
        default_factory=list,
        title="Task names"
    )
    template_name: str = Field("", title="Template name")


class IntegrateHeroTemplateNameProfileModel(BaseSettingsModel):
    product_types: list[str] = Field(
        default_factory=list,
        title="Product types"
    )
    hosts: list[str] = Field(
        default_factory=list,
        title="Hosts"
    )
    task_types: list[str] = Field(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    task_names: list[str] = Field(
        default_factory=list,
        title="Task names"
    )
    template_name: str = Field("", title="Template name")


class IntegrateHeroVersionModel(BaseSettingsModel):
    _isGroup = True
    enabled: bool = Field(True)
    optional: bool = Field(False, title="Optional")
    active: bool = Field(True, title="Active")
    families: list[str] = Field(default_factory=list, title="Families")
    # TODO remove when removed from client code
    template_name_profiles: list[IntegrateHeroTemplateNameProfileModel] = (
        Field(
            default_factory=list,
            title="Template name profiles"
        )
    )


class CleanUpModel(BaseSettingsModel):
    _isGroup = True
    paterns: list[str] = Field(
        default_factory=list,
        title="Patterns (regex)"
    )
    remove_temp_renders: bool = Field(False, title="Remove Temp renders")


class CleanUpFarmModel(BaseSettingsModel):
    _isGroup = True
    enabled: bool = Field(True)


class PublishPuginsModel(BaseSettingsModel):
    CollectAnatomyInstanceData: CollectAnatomyInstanceDataModel = Field(
        default_factory=CollectAnatomyInstanceDataModel,
        title="Collect Anatomy Instance Data"
    )
    CollectAudio: CollectAudioModel = Field(
        default_factory=CollectAudioModel,
        title="Collect Audio"
    )
    CollectSceneVersion: CollectSceneVersionModel = Field(
        default_factory=CollectSceneVersionModel,
        title="Collect Version from Workfile"
    )
    collect_comment_per_instance: CollectCommentPIModel = Field(
        default_factory=CollectCommentPIModel,
        title="Collect comment per instance",
    )
    CollectFramesFixDef: CollectFramesFixDefModel = Field(
        default_factory=CollectFramesFixDefModel,
        title="Collect Frames to Fix",
    )
    ValidateEditorialAssetName: ValidateBaseModel = Field(
        default_factory=ValidateBaseModel,
        title="Validate Editorial Asset Name"
    )
    ValidateVersion: ValidateBaseModel = Field(
        default_factory=ValidateBaseModel,
        title="Validate Version"
    )
    ValidateIntent: ValidateIntentModel = Field(
        default_factory=ValidateIntentModel,
        title="Validate Intent"
    )
    ExtractThumbnail: ExtractThumbnailModel = Field(
        default_factory=ExtractThumbnailModel,
        title="Extract Thumbnail"
    )
    ExtractOIIOTranscode: ExtractOIIOTranscodeModel = Field(
        default_factory=ExtractOIIOTranscodeModel,
        title="Extract OIIO Transcode"
    )
    ExtractReview: ExtractReviewModel = Field(
        default_factory=ExtractReviewModel,
        title="Extract Review"
    )
    ExtractBurnin: ExtractBurninModel = Field(
        default_factory=ExtractBurninModel,
        title="Extract Burnin"
    )
    PreIntegrateThumbnails: PreIntegrateThumbnailsModel = Field(
        default_factory=PreIntegrateThumbnailsModel,
        title="Override Integrate Thumbnail Representations"
    )
    IntegrateProductGroup: IntegrateProductGroupModel = Field(
        default_factory=IntegrateProductGroupModel,
        title="Integrate Product Group"
    )
    IntegrateHeroVersion: IntegrateHeroVersionModel = Field(
        default_factory=IntegrateHeroVersionModel,
        title="Integrate Hero Version"
    )
    CleanUp: CleanUpModel = Field(
        default_factory=CleanUpModel,
        title="Clean Up"
    )
    CleanUpFarm: CleanUpFarmModel = Field(
        default_factory=CleanUpFarmModel,
        title="Clean Up Farm"
    )


DEFAULT_PUBLISH_VALUES = {
    "CollectAnatomyInstanceData": {
        "follow_workfile_version": False
    },
    "CollectAudio": {
        "enabled": False,
        "audio_product_name": "audioMain"
    },
    "CollectSceneVersion": {
        "hosts": [
            "aftereffects",
            "blender",
            "celaction",
            "fusion",
            "harmony",
            "hiero",
            "houdini",
            "maya",
            "nuke",
            "photoshop",
            "resolve",
            "tvpaint"
        ],
        "skip_hosts_headless_publish": []
    },
    "collect_comment_per_instance": {
        "enabled": False,
        "families": []
    },
    "CollectFramesFixDef": {
        "enabled": True,
        "rewrite_version_enable": True
    },
    "ValidateEditorialAssetName": {
        "enabled": True,
        "optional": False,
        "active": True
    },
    "ValidateVersion": {
        "enabled": True,
        "optional": False,
        "active": True
    },
    "ValidateIntent": {
        "enabled": False,
        "profiles": []
    },
    "ExtractThumbnail": {
        "enabled": True,
        "ffmpeg_args": {
            "input": [
                "-apply_trc gamma22"
            ],
            "output": []
        }
    },
    "ExtractOIIOTranscode": {
        "enabled": True,
        "profiles": []
    },
    "ExtractReview": {
        "enabled": True,
        "profiles": [
            {
                "product_types": [],
                "hosts": [],
                "outputs": [
                    {
                        "name": "png",
                        "ext": "png",
                        "tags": [
                            "ftrackreview",
                            "kitsureview"
                        ],
                        "burnins": [],
                        "ffmpeg_args": {
                            "video_filters": [],
                            "audio_filters": [],
                            "input": [],
                            "output": []
                        },
                        "filter": {
                            "families": [
                                "render",
                                "review",
                                "ftrack"
                            ],
                            "product_names": [],
                            "custom_tags": [],
                            "single_frame_filter": "single_frame"
                        },
                        "overscan_crop": "",
                        "overscan_color": [0, 0, 0, 1.0],
                        "width": 1920,
                        "height": 1080,
                        "scale_pixel_aspect": True,
                        "bg_color": [0, 0, 0, 0.0],
                        "letter_box": {
                            "enabled": False,
                            "ratio": 0.0,
                            "fill_color": [0, 0, 0, 1.0],
                            "line_thickness": 0,
                            "line_color": [255, 0, 0, 1.0]
                        }
                    },
                    {
                        "name": "h264",
                        "ext": "mp4",
                        "tags": [
                            "burnin",
                            "ftrackreview",
                            "kitsureview"
                        ],
                        "burnins": [],
                        "ffmpeg_args": {
                            "video_filters": [],
                            "audio_filters": [],
                            "input": [
                                "-apply_trc gamma22"
                            ],
                            "output": [
                                "-pix_fmt yuv420p",
                                "-crf 18",
                                "-intra"
                            ]
                        },
                        "filter": {
                            "families": [
                                "render",
                                "review",
                                "ftrack"
                            ],
                            "product_names": [],
                            "custom_tags": [],
                            "single_frame_filter": "multi_frame"
                        },
                        "overscan_crop": "",
                        "overscan_color": [0, 0, 0, 1.0],
                        "width": 0,
                        "height": 0,
                        "scale_pixel_aspect": True,
                        "bg_color": [0, 0, 0, 0.0],
                        "letter_box": {
                            "enabled": False,
                            "ratio": 0.0,
                            "fill_color": [0, 0, 0, 1.0],
                            "line_thickness": 0,
                            "line_color": [255, 0, 0, 1.0]
                        }
                    }
                ]
            }
        ]
    },
    "ExtractBurnin": {
        "enabled": True,
        "options": {
            "font_size": 42,
            "font_color": [255, 255, 255, 1.0],
            "bg_color": [0, 0, 0, 0.5],
            "x_offset": 5,
            "y_offset": 5,
            "bg_padding": 5,
            "font_filepath": {
                "windows": "",
                "darwin": "",
                "linux": ""
            }
        },
        "profiles": [
            {
                "product_types": [],
                "hosts": [],
                "task_types": [],
                "task_names": [],
                "product_names": [],
                "burnins": [
                    {
                        "name": "burnin",
                        "TOP_LEFT": "{yy}-{mm}-{dd}",
                        "TOP_CENTERED": "",
                        "TOP_RIGHT": "{anatomy[version]}",
                        "BOTTOM_LEFT": "{username}",
                        "BOTTOM_CENTERED": "{folder[name]}",
                        "BOTTOM_RIGHT": "{frame_start}-{current_frame}-{frame_end}",
                        "filter": {
                            "families": [],
                            "tags": []
                        }
                    },
                ]
            },
            {
                "product_types": ["review"],
                "hosts": [
                    "maya",
                    "houdini",
                    "max"
                ],
                "task_types": [],
                "task_names": [],
                "product_names": [],
                "burnins": [
                    {
                        "name": "focal_length_burnin",
                        "TOP_LEFT": "{yy}-{mm}-{dd}",
                        "TOP_CENTERED": "{focalLength:.2f} mm",
                        "TOP_RIGHT": "{anatomy[version]}",
                        "BOTTOM_LEFT": "{username}",
                        "BOTTOM_CENTERED": "{folder[name]}",
                        "BOTTOM_RIGHT": "{frame_start}-{current_frame}-{frame_end}",
                        "filter": {
                            "families": [],
                            "tags": []
                        }
                    }
                ]
            }
        ]
    },
    "PreIntegrateThumbnails": {
        "enabled": True,
        "integrate_profiles": []
    },
    "IntegrateProductGroup": {
        "product_grouping_profiles": [
            {
                "product_types": [],
                "hosts": [],
                "task_types": [],
                "tasks": [],
                "template": ""
            }
        ]
    },
    "IntegrateHeroVersion": {
        "enabled": True,
        "optional": True,
        "active": True,
        "families": [
            "model",
            "rig",
            "look",
            "pointcache",
            "animation",
            "setdress",
            "layout",
            "mayaScene",
            "simpleUnrealTexture"
        ],
        "template_name_profiles": [
            {
                "product_types": [
                    "simpleUnrealTexture"
                ],
                "hosts": [
                    "standalonepublisher"
                ],
                "task_types": [],
                "task_names": [],
                "template_name": "simpleUnrealTextureHero"
            }
        ]
    },
    "CleanUp": {
        "paterns": [],
        "remove_temp_renders": False
    },
    "CleanUpFarm": {
        "enabled": False
    }
}
