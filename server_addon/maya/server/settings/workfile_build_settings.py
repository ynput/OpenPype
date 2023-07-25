from pydantic import Field
from ayon_server.settings import BaseSettingsModel, task_types_enum


class ContextItemModel(BaseSettingsModel):
    _layout = "expanded"
    product_name_filters: list[str] = Field(
        default_factory=list, title="Product name Filters")
    product_types: list[str] = Field(default_factory=list, title="Product types")
    repre_names: list[str] = Field(default_factory=list, title="Repre Names")
    loaders: list[str] = Field(default_factory=list, title="Loaders")


class WorkfileSettingModel(BaseSettingsModel):
    _layout = "expanded"
    task_types: list[str] = Field(default_factory=list,
        enum_resolver=task_types_enum, title="Task types")
    tasks: list[str] = Field(default_factory=list, title="Task names")
    current_context: list[ContextItemModel] = Field(
        default_factory=list,
        title="Current Context")
    linked_assets: list[ContextItemModel] = Field(
        default_factory=list,
        title="Linked Assets")


class ProfilesModel(BaseSettingsModel):
    profiles: list[WorkfileSettingModel] = Field(
        default_factory=list,
        title="Profiles"
    )


DEFAULT_WORKFILE_SETTING = {
    "profiles": [
        {
            "task_types": [],
            "tasks": [
                "Lighting"
            ],
            "current_context": [
                {
                    "product_name_filters": [
                        ".+[Mm]ain"
                    ],
                    "product_types": [
                        "model"
                    ],
                    "repre_names": [
                        "abc",
                        "ma"
                    ],
                    "loaders": [
                        "ReferenceLoader"
                    ]
                },
                {
                    "product_name_filters": [],
                    "product_types": [
                        "animation",
                        "pointcache",
                        "proxyAbc"
                    ],
                    "repre_names": [
                        "abc"
                    ],
                    "loaders": [
                        "ReferenceLoader"
                    ]
                },
                {
                    "product_name_filters": [],
                    "product_types": [
                        "rendersetup"
                    ],
                    "repre_names": [
                        "json"
                    ],
                    "loaders": [
                        "RenderSetupLoader"
                    ]
                },
                {
                    "product_name_filters": [],
                    "product_types": [
                        "camera"
                    ],
                    "repre_names": [
                        "abc"
                    ],
                    "loaders": [
                        "ReferenceLoader"
                    ]
                }
            ],
            "linked_assets": [
                {
                    "product_name_filters": [],
                    "product_types": [
                        "sedress"
                    ],
                    "repre_names": [
                        "ma"
                    ],
                    "loaders": [
                        "ReferenceLoader"
                    ]
                },
                {
                    "product_name_filters": [],
                    "product_types": [
                        "ArnoldStandin"
                    ],
                    "repre_names": [
                        "ass"
                    ],
                    "loaders": [
                        "assLoader"
                    ]
                }
            ]
        }
    ]
}
