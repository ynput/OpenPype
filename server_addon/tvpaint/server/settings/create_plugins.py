from pydantic import Field
from ayon_server.settings import BaseSettingsModel


class CreateWorkfileModel(BaseSettingsModel):
    enabled: bool = Field(True)
    default_variant: str = Field(title="Default variant")
    default_variants: list[str] = Field(
        default_factory=list, title="Default variants")


class CreateReviewModel(BaseSettingsModel):
    enabled: bool = Field(True)
    active_on_create: bool = Field(True, title="Active by default")
    default_variant: str = Field(title="Default variant")
    default_variants: list[str] = Field(
        default_factory=list, title="Default variants")


class CreateRenderSceneModel(BaseSettingsModel):
    enabled: bool = Field(True)
    active_on_create: bool = Field(True, title="Active by default")
    mark_for_review: bool  = Field(True, title="Review by default")
    default_pass_name: str = Field(title="Default beauty pass")
    default_variant: str = Field(title="Default variant")
    default_variants: list[str] = Field(
        default_factory=list, title="Default variants")


class CreateRenderLayerModel(BaseSettingsModel):
    mark_for_review: bool = Field(True, title="Review by default")
    default_pass_name: str = Field(title="Default beauty pass")
    default_variant: str = Field(title="Default variant")
    default_variants: list[str] = Field(
        default_factory=list, title="Default variants")


class CreateRenderPassModel(BaseSettingsModel):
    mark_for_review: bool = Field(True, title="Review by default")
    default_variant: str = Field(title="Default variant")
    default_variants: list[str] = Field(
        default_factory=list, title="Default variants")


class AutoDetectCreateRenderModel(BaseSettingsModel):
    """The creator tries to auto-detect Render Layers and Render Passes in scene.

    For Render Layers is used group name as a variant and for Render Passes is
    used TVPaint layer name.

    Group names can be renamed by their used order in scene. The renaming
    template where can be used '{group_index}' formatting key which is
    filled by "used position index of group".
    - Template: 'L{group_index}'
    - Group offset: '10'
    - Group padding: '3'

    Would create group names "L010", "L020", ...
    """

    enabled: bool = Field(True)
    allow_group_rename: bool = Field(title="Allow group rename")
    group_name_template: str = Field(title="Group name template")
    group_idx_offset: int = Field(1, title="Group index Offset", ge=1)
    group_idx_padding: int = Field(4, title="Group index Padding", ge=1)


class CreatePluginsModel(BaseSettingsModel):
    create_workfile: CreateWorkfileModel = Field(
        default_factory=CreateWorkfileModel,
        title="Create Workfile"
    )
    create_review: CreateReviewModel = Field(
        default_factory=CreateReviewModel,
        title="Create Review"
    )
    create_render_scene: CreateRenderSceneModel = Field(
        default_factory=CreateReviewModel,
        title="Create Render Scene"
    )
    create_render_layer: CreateRenderLayerModel= Field(
        default_factory=CreateRenderLayerModel,
        title="Create Render Layer"
    )
    create_render_pass: CreateRenderPassModel = Field(
        default_factory=CreateRenderPassModel,
        title="Create Render Pass"
    )
    auto_detect_render: AutoDetectCreateRenderModel = Field(
        default_factory=AutoDetectCreateRenderModel,
        title="Auto-Detect Create Render",
    )


DEFAULT_CREATE_SETTINGS = {
    "create_workfile": {
        "enabled": True,
        "default_variant": "Main",
        "default_variants": []
    },
    "create_review": {
        "enabled": True,
        "active_on_create": True,
        "default_variant": "Main",
        "default_variants": []
    },
    "create_render_scene": {
        "enabled": True,
        "active_on_create": False,
        "mark_for_review": True,
        "default_pass_name": "beauty",
        "default_variant": "Main",
        "default_variants": []
    },
    "create_render_layer": {
        "mark_for_review": False,
        "default_pass_name": "beauty",
        "default_variant": "Main",
        "default_variants": []
    },
    "create_render_pass": {
        "mark_for_review": False,
        "default_variant": "Main",
        "default_variants": []
    },
    "auto_detect_render": {
        "enabled": False,
        "allow_group_rename": True,
        "group_name_template": "L{group_index}",
        "group_idx_offset": 10,
        "group_idx_padding": 3
    }
}
