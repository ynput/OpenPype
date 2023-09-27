from pydantic import Field
from ayon_server.settings import BaseSettingsModel


class HoudiniVarModel(BaseSettingsModel):
    _layout = "expanded"
    var: str = Field("", title="Var")
    path: str = Field(default_factory="", title="Path")


class UpdateHoudiniVarcontextModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")
    # TODO this was dynamic dictionary '{var: path}'
    houdini_vars: list[HoudiniVarModel] = Field(
        default_factory=list,
        title="Houdini Vars"
    )


class GeneralSettingsModel(BaseSettingsModel):
    update_houdini_var_context: UpdateHoudiniVarcontextModel = Field(
        default_factory=UpdateHoudiniVarcontextModel,
        title="Update Houdini Vars on context change"
    )


DEFAULT_GENERAL_SETTINGS = {
    "update_houdini_var_context": {
        "enabled": True,
        "houdini_vars": [
            {
                "var": "JOB",
                "path": "{root[work]}/{project[name]}/{hierarchy}/{asset}/work/{task[name]}"  # noqa
            }
        ]
    }
}
