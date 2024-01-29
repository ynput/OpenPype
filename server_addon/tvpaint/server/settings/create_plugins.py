from ayon_server.settings import BaseSettingsModel, SettingsField


class CreateWorkfileModel(BaseSettingsModel):
    enabled: bool = SettingsField(True)
    default_variant: str = SettingsField(title="Default variant")
    default_variants: list[str] = SettingsField(
        default_factory=list, title="Default variants")


class CreateReviewModel(BaseSettingsModel):
    enabled: bool = SettingsField(True)
    active_on_create: bool = SettingsField(True, title="Active by default")
    default_variant: str = SettingsField(title="Default variant")
    default_variants: list[str] = SettingsField(
        default_factory=list, title="Default variants")


class CreateRenderSceneModel(BaseSettingsModel):
    enabled: bool = SettingsField(True)
    active_on_create: bool = SettingsField(True, title="Active by default")
    mark_for_review: bool = SettingsField(True, title="Review by default")
    default_pass_name: str = SettingsField(title="Default beauty pass")
    default_variant: str = SettingsField(title="Default variant")
    default_variants: list[str] = SettingsField(
        default_factory=list, title="Default variants")


class CreateRenderLayerModel(BaseSettingsModel):
    mark_for_review: bool = SettingsField(True, title="Review by default")
    default_pass_name: str = SettingsField(title="Default beauty pass")
    default_variant: str = SettingsField(title="Default variant")
    default_variants: list[str] = SettingsField(
        default_factory=list, title="Default variants")


class CreateRenderPassModel(BaseSettingsModel):
    mark_for_review: bool = SettingsField(True, title="Review by default")
    default_variant: str = SettingsField(title="Default variant")
    default_variants: list[str] = SettingsField(
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

    enabled: bool = SettingsField(True)
    allow_group_rename: bool = SettingsField(title="Allow group rename")
    group_name_template: str = SettingsField(title="Group name template")
    group_idx_offset: int = SettingsField(
        1, title="Group index Offset", ge=1
    )
    group_idx_padding: int = SettingsField(
        4, title="Group index Padding", ge=1
    )


class CreatePluginsModel(BaseSettingsModel):
    create_workfile: CreateWorkfileModel = SettingsField(
        default_factory=CreateWorkfileModel,
        title="Create Workfile"
    )
    create_review: CreateReviewModel = SettingsField(
        default_factory=CreateReviewModel,
        title="Create Review"
    )
    create_render_scene: CreateRenderSceneModel = SettingsField(
        default_factory=CreateReviewModel,
        title="Create Render Scene"
    )
    create_render_layer: CreateRenderLayerModel = SettingsField(
        default_factory=CreateRenderLayerModel,
        title="Create Render Layer"
    )
    create_render_pass: CreateRenderPassModel = SettingsField(
        default_factory=CreateRenderPassModel,
        title="Create Render Pass"
    )
    auto_detect_render: AutoDetectCreateRenderModel = SettingsField(
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
