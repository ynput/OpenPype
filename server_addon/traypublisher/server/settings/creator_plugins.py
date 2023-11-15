from pydantic import Field

from ayon_server.settings import BaseSettingsModel


class BatchMovieCreatorPlugin(BaseSettingsModel):
    """Allows to publish multiple video files in one go. <br />Name of matching
     asset is parsed from file names ('asset.mov', 'asset_v001.mov',
     'my_asset_to_publish.mov')"""

    default_variants: list[str] = Field(
        title="Default variants",
        default_factory=list
    )

    default_tasks: list[str] = Field(
        title="Default tasks",
        default_factory=list
    )

    extensions: list[str] = Field(
        title="Extensions",
        default_factory=list
    )


class TrayPublisherCreatePluginsModel(BaseSettingsModel):
    BatchMovieCreator: BatchMovieCreatorPlugin = Field(
        title="Batch Movie Creator",
        default_factory=BatchMovieCreatorPlugin
    )


DEFAULT_CREATORS = {
    "BatchMovieCreator": {
        "default_variants": [
            "Main"
        ],
        "default_tasks": [
            "Compositing"
        ],
        "extensions": [
            ".mov"
        ]
    },
}
