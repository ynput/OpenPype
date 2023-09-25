from pydantic import Field
from ayon_server.settings import BaseSettingsModel


class JobPathModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")
    path: str = Field(title="Path")


class GeneralSettingsModel(BaseSettingsModel):
    JobPath: JobPathModel = Field(
        default_factory=JobPathModel,
        title="JOB Path"
    )


DEFAULT_GENERAL_SETTINGS = {
    "JobPath": {
        "enabled": True,
        "path": "{root[work]}/{project[name]}/{hierarchy}/{asset}/work/{task[name]}"  # noqa
    }
}
