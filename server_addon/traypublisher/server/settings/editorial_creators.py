from pydantic import Field

from ayon_server.settings import BaseSettingsModel, task_types_enum


class ClipNameTokenizerItem(BaseSettingsModel):
    _layout = "expanded"
    # TODO was 'dict-modifiable', is list of dicts now, must be fixed in code
    name: str = Field("#TODO", title="Tokenizer name")
    regex: str = Field("", title="Tokenizer regex")


class ShotAddTasksItem(BaseSettingsModel):
    _layout = "expanded"
    # TODO was 'dict-modifiable', is list of dicts now, must be fixed in code
    name: str = Field('', title="Key")
    task_type: list[str] = Field(
        title="Task type",
        default_factory=list,
        enum_resolver=task_types_enum)


class ShotRenameSubmodel(BaseSettingsModel):
    enabled: bool = True
    shot_rename_template: str = Field(
        "",
        title="Shot rename template"
    )


parent_type_enum = [
    {"value": "Project", "label": "Project"},
    {"value": "Folder", "label": "Folder"},
    {"value": "Episode", "label": "Episode"},
    {"value": "Sequence", "label": "Sequence"},
]


class TokenToParentConvertorItem(BaseSettingsModel):
    # TODO - was 'type' must be renamed in code to `parent_type`
    parent_type: str = Field(
        "Project",
        enum_resolver=lambda: parent_type_enum
    )
    name: str = Field(
        "",
        title="Parent token name",
        description="Unique name used in `Parent path template`"
    )
    value: str = Field(
        "",
        title="Parent token value",
        description="Template where any text, Anatomy keys and Tokens could be used"  # noqa
    )


class ShotHierchySubmodel(BaseSettingsModel):
    enabled: bool = True
    parents_path: str = Field(
        "",
        title="Parents path template",
        description="Using keys from \"Token to parent convertor\" or tokens directly"  # noqa
    )
    parents: list[TokenToParentConvertorItem] = Field(
        default_factory=TokenToParentConvertorItem,
        title="Token to parent convertor"
    )


output_file_type = [
    {"value": ".mp4", "label": "MP4"},
    {"value": ".mov", "label": "MOV"},
    {"value": ".wav", "label": "WAV"}
]


class ProductTypePresetItem(BaseSettingsModel):
    product_type: str = Field("", title="Product type")
    # TODO add placeholder '< Inherited >'
    variant: str = Field("", title="Variant")
    review: bool = Field(True, title="Review")
    output_file_type: str = Field(
        ".mp4",
        enum_resolver=lambda: output_file_type
    )


class EditorialSimpleCreatorPlugin(BaseSettingsModel):
    default_variants: list[str] = Field(
        default_factory=list,
        title="Default Variants"
    )
    clip_name_tokenizer: list[ClipNameTokenizerItem] = Field(
        default_factory=ClipNameTokenizerItem,
        description=(
            "Using Regex expression to create tokens. \nThose can be used"
            " later in \"Shot rename\" creator \nor \"Shot hierarchy\"."
            "\n\nTokens should be decorated with \"_\" on each side"
        )
    )
    shot_rename: ShotRenameSubmodel = Field(
        title="Shot Rename",
        default_factory=ShotRenameSubmodel
    )
    shot_hierarchy: ShotHierchySubmodel = Field(
        title="Shot Hierarchy",
        default_factory=ShotHierchySubmodel
    )
    shot_add_tasks: list[ShotAddTasksItem] = Field(
        title="Add tasks to shot",
        default_factory=ShotAddTasksItem
    )
    product_type_presets: list[ProductTypePresetItem] = Field(
        default_factory=list
    )


class TraypublisherEditorialCreatorPlugins(BaseSettingsModel):
    editorial_simple: EditorialSimpleCreatorPlugin = Field(
        title="Editorial simple creator",
        default_factory=EditorialSimpleCreatorPlugin,
    )


DEFAULT_EDITORIAL_CREATORS = {
    "editorial_simple": {
        "default_variants": [
            "Main"
        ],
        "clip_name_tokenizer": [
            {"name": "_sequence_", "regex": "(sc\\d{3})"},
            {"name": "_shot_", "regex": "(sh\\d{3})"}
        ],
        "shot_rename": {
            "enabled": True,
            "shot_rename_template": "{project[code]}_{_sequence_}_{_shot_}"
        },
        "shot_hierarchy": {
            "enabled": True,
            "parents_path": "{project}/{folder}/{sequence}",
            "parents": [
                {
                    "parent_type": "Project",
                    "name": "project",
                    "value": "{project[name]}"
                },
                {
                    "parent_type": "Folder",
                    "name": "folder",
                    "value": "shots"
                },
                {
                    "parent_type": "Sequence",
                    "name": "sequence",
                    "value": "{_sequence_}"
                }
            ]
        },
        "shot_add_tasks": [],
        "product_type_presets": [
            {
                "product_type": "review",
                "variant": "Reference",
                "review": True,
                "output_file_type": ".mp4"
            },
            {
                "product_type": "plate",
                "variant": "",
                "review": False,
                "output_file_type": ".mov"
            },
            {
                "product_type": "audio",
                "variant": "",
                "review": False,
                "output_file_type": ".wav"
            }
        ]
    }
}
