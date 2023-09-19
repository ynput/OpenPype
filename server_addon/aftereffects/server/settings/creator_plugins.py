from pydantic import Field

from ayon_server.settings import BaseSettingsModel


class CreateRenderPlugin(BaseSettingsModel):
    mark_for_review: bool = Field(True, title="Review")
    default_variants: list[str] = Field(
        default_factory=list,
        title="Default Variants"
    )


class AfterEffectsCreatorPlugins(BaseSettingsModel):
    RenderCreator: CreateRenderPlugin = Field(
        title="Create Render",
        default_factory=CreateRenderPlugin,
    )
