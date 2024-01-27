from ayon_server.settings import BaseSettingsModel, SettingsField
from .imageio import CelActionImageIOModel


class CollectRenderPathModel(BaseSettingsModel):
    output_extension: str = SettingsField(
        "",
        title="Output render file extension"
    )
    anatomy_template_key_render_files: str = SettingsField(
        "",
        title="Anatomy template key: render files"
    )
    anatomy_template_key_metadata: str = SettingsField(
        "",
        title="Anatomy template key: metadata job file"
    )


def _workfile_submit_overrides():
    return [
        {
            "value": "render_chunk",
            "label": "Pass chunk size"
        },
        {
            "value": "frame_range",
            "label": "Pass frame range"
        },
        {
            "value": "resolution",
            "label": "Pass resolution"
        }
    ]


class WorkfileModel(BaseSettingsModel):
    submission_overrides: list[str] = SettingsField(
        default_factory=list,
        title="Submission workfile overrides",
        enum_resolver=_workfile_submit_overrides
    )


class PublishPuginsModel(BaseSettingsModel):
    CollectRenderPath: CollectRenderPathModel = SettingsField(
        default_factory=CollectRenderPathModel,
        title="Collect Render Path"
    )


class CelActionSettings(BaseSettingsModel):
    imageio: CelActionImageIOModel = SettingsField(
        default_factory=CelActionImageIOModel,
        title="Color Management (ImageIO)"
    )
    workfile: WorkfileModel = SettingsField(
        title="Workfile"
    )
    publish: PublishPuginsModel = SettingsField(
        default_factory=PublishPuginsModel,
        title="Publish plugins",
    )


DEFAULT_VALUES = {
    "imageio": {
        "ocio_config": {
            "enabled": False,
            "filepath": []
        },
        "file_rules": {
            "enabled": False,
            "rules": []
        }
    },
    "workfile": {
        "submission_overrides": [
            "render_chunk",
            "frame_range",
            "resolution"
        ]
    },
    "publish": {
        "CollectRenderPath": {
            "output_extension": "png",
            "anatomy_template_key_render_files": "render",
            "anatomy_template_key_metadata": "render"
        }
    }
}
