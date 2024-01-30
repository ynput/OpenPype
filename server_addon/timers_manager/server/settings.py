from ayon_server.settings import BaseSettingsModel, SettingsField


class TimersManagerSettings(BaseSettingsModel):
    auto_stop: bool = SettingsField(
        True,
        title="Auto stop timer",
        scope=["studio"],
    )
    full_time: int = SettingsField(
        15,
        title="Max idle time",
        scope=["studio"],
    )
    message_time: float = SettingsField(
        0.5,
        title="When dialog will show",
        scope=["studio"],
    )
    disregard_publishing: bool = SettingsField(
        False,
        title="Disregard publishing",
        scope=["studio"],
    )
