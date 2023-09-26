from pydantic import Field
from ayon_server.settings import BaseSettingsModel


class UpdateJobVarcontextModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")
    job_path: str = Field(title="JOB Path")


class GeneralSettingsModel(BaseSettingsModel):
    update_job_var_context: UpdateJobVarcontextModel = Field(
        default_factory=UpdateJobVarcontextModel,
        title="Update $JOB on context change"
    )


DEFAULT_GENERAL_SETTINGS = {
    "update_job_var_context": {
        "enabled": True,
        "job_path": "{root[work]}/{project[name]}/{hierarchy}/{asset}/work/{task[name]}"  # noqa
    }
}
