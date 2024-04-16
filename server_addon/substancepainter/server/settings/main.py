from ayon_server.settings import BaseSettingsModel, SettingsField
from .imageio import ImageIOSettings, DEFAULT_IMAGEIO_SETTINGS


def normal_map_format_enum():
    return [
        {"label": "DirectX", "value": "DirectX"},
        {"label": "OpenGL", "value": "OpenGL"},
    ]


def tangent_space_enum():
    return [
        {"label": "PerFragment", "value": "PerFragment"},
        {"label": "PerVertex", "value": "PerVertex"},
    ]


def uv_workflow_enum():
    return [
        {"label": "Default", "value": "default"},
        {"label": "UV Tile", "value": "uvTile"},
        {"label": "Texture Set Per UV Tile",
         "value": "textureSetPerUVTile"}
    ]


def document_resolution_enum():
    return [
        {"label": "128", "value": 128},
        {"label": "256", "value": 256},
        {"label": "512", "value": 512},
        {"label": "1024", "value": 1024},
        {"label": "2048", "value": 2048},
        {"label": "4096", "value": 4096}
    ]


class ProjectTemplatesModel(BaseSettingsModel):
    _layout = "expanded"
    name: str = SettingsField(title="Template Name")
    document_resolution: int = SettingsField(
        1024, enum_resolver=document_resolution_enum,
        title="Document Resolution",
        description=("Set texture resolution when "
                     "creating new project.")
    )
    normal_map_format: str = SettingsField(
        "DirectX", enum_resolver=normal_map_format_enum,
        title="Normal Map Format",
        description=("Set normal map format when "
                     "creating new project.")
    )
    tangent_space: str = SettingsField(
        "PerFragment", enum_resolver=tangent_space_enum,
        title="Tangent Space",
        description=("An option to compute tangent space "
                     "when creating new project.")
    )
    uv_workflow: str = SettingsField(
        "default", enum_resolver=uv_workflow_enum,
        title="UV Tile Settings",
        description=("Set UV workflow when "
                     "creating new project.")
    )
    import_cameras: bool = SettingsField(
        True, title="Import Cameras",
        description="Import cameras from the mesh file.")
    preserve_strokes: bool = SettingsField(
        True, title="Preserve Strokes",
        description=("Preserve strokes positions on mesh.\n"
                     "(only relevant when loading into "
                     "existing project)")
    )


class ShelvesSettingsModel(BaseSettingsModel):
    _layout = "compact"
    name: str = SettingsField(title="Name")
    value: str = SettingsField(title="Path")


class SubstancePainterSettings(BaseSettingsModel):
    imageio: ImageIOSettings = SettingsField(
        default_factory=ImageIOSettings,
        title="Color Management (ImageIO)"
    )
    shelves: list[ShelvesSettingsModel] = SettingsField(
        default_factory=list,
        title="Shelves"
    )
    project_templates:  list[ProjectTemplatesModel] = SettingsField(
        default_factory=ProjectTemplatesModel,
        title="Project Templates"
    )


DEFAULT_SPAINTER_SETTINGS = {
    "imageio": DEFAULT_IMAGEIO_SETTINGS,
    "shelves": [],
    "project_templates": [],
}
