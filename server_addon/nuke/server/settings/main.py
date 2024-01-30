from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    ensure_unique_names
)

from .general import (
    GeneralSettings,
    DEFAULT_GENERAL_SETTINGS
)
from .imageio import (
    ImageIOSettings,
    DEFAULT_IMAGEIO_SETTINGS
)
from .dirmap import (
    DirmapSettings,
    DEFAULT_DIRMAP_SETTINGS
)
from .scriptsmenu import (
    ScriptsmenuSettings,
    DEFAULT_SCRIPTSMENU_SETTINGS
)
from .gizmo import (
    GizmoItem,
    DEFAULT_GIZMO_ITEM
)
from .create_plugins import (
    CreatorPluginsSettings,
    DEFAULT_CREATE_SETTINGS
)
from .publish_plugins import (
    PublishPuginsModel,
    DEFAULT_PUBLISH_PLUGIN_SETTINGS
)
from .loader_plugins import (
    LoaderPuginsModel,
    DEFAULT_LOADER_PLUGINS_SETTINGS
)
from .workfile_builder import (
    WorkfileBuilderModel,
    DEFAULT_WORKFILE_BUILDER_SETTINGS
)
from .templated_workfile_build import (
    TemplatedWorkfileBuildModel
)


class NukeSettings(BaseSettingsModel):
    """Nuke addon settings."""

    general: GeneralSettings = SettingsField(
        default_factory=GeneralSettings,
        title="General",
    )

    imageio: ImageIOSettings = SettingsField(
        default_factory=ImageIOSettings,
        title="Color Management (imageio)",
    )

    dirmap: DirmapSettings = SettingsField(
        default_factory=DirmapSettings,
        title="Nuke Directory Mapping",
    )

    scriptsmenu: ScriptsmenuSettings = SettingsField(
        default_factory=ScriptsmenuSettings,
        title="Scripts Menu Definition",
    )

    gizmo: list[GizmoItem] = SettingsField(
        default_factory=list, title="Gizmo Menu")

    create: CreatorPluginsSettings = SettingsField(
        default_factory=CreatorPluginsSettings,
        title="Creator Plugins",
    )

    publish: PublishPuginsModel = SettingsField(
        default_factory=PublishPuginsModel,
        title="Publish Plugins",
    )

    load: LoaderPuginsModel = SettingsField(
        default_factory=LoaderPuginsModel,
        title="Loader Plugins",
    )

    workfile_builder: WorkfileBuilderModel = SettingsField(
        default_factory=WorkfileBuilderModel,
        title="Workfile Builder",
    )

    templated_workfile_build: TemplatedWorkfileBuildModel = SettingsField(
        title="Templated Workfile Build",
        default_factory=TemplatedWorkfileBuildModel
    )


DEFAULT_VALUES = {
    "general": DEFAULT_GENERAL_SETTINGS,
    "imageio": DEFAULT_IMAGEIO_SETTINGS,
    "dirmap": DEFAULT_DIRMAP_SETTINGS,
    "scriptsmenu": DEFAULT_SCRIPTSMENU_SETTINGS,
    "gizmo": [DEFAULT_GIZMO_ITEM],
    "create": DEFAULT_CREATE_SETTINGS,
    "publish": DEFAULT_PUBLISH_PLUGIN_SETTINGS,
    "load": DEFAULT_LOADER_PLUGINS_SETTINGS,
    "workfile_builder": DEFAULT_WORKFILE_BUILDER_SETTINGS,
    "templated_workfile_build": {
        "profiles": []
    }
}
