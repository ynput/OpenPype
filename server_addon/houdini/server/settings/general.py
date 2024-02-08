from ayon_server.settings import BaseSettingsModel, SettingsField


class HoudiniVarModel(BaseSettingsModel):
    _layout = "expanded"
    var: str = SettingsField("", title="Var")
    value: str = SettingsField("", title="Value")
    is_directory: bool = SettingsField(False, title="Treat as directory")


class UpdateHoudiniVarcontextModel(BaseSettingsModel):
    """Sync vars with context changes.

    If a value is treated as a directory on update
    it will be ensured the folder exists.
    """

    enabled: bool = SettingsField(title="Enabled")
    # TODO this was dynamic dictionary '{var: path}'
    houdini_vars: list[HoudiniVarModel] = SettingsField(
        default_factory=list,
        title="Houdini Vars"
    )


class GeneralSettingsModel(BaseSettingsModel):
    add_self_publish_button: bool = SettingsField(
        False,
        title="Add Self Publish Button"
    )
    update_houdini_var_context: UpdateHoudiniVarcontextModel = SettingsField(
        default_factory=UpdateHoudiniVarcontextModel,
        title="Update Houdini Vars on context change"
    )


DEFAULT_GENERAL_SETTINGS = {
    "add_self_publish_button": False,
    "update_houdini_var_context": {
        "enabled": True,
        "houdini_vars": [
            {
                "var": "JOB",
                "value": "{root[work]}/{project[name]}/{hierarchy}/{asset}/work/{task[name]}",  # noqa
                "is_directory": True
            }
        ]
    }
}
