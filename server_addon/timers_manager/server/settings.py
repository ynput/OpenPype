from pydantic import Field
from ayon_server.settings import BaseSettingsModel


class TimersManagerSettings(BaseSettingsModel):
    auto_stop: bool = Field(True, title="Auto stop timer")
    full_time: int = Field(15, title="Max idle time")
    message_time: float = Field(0.5, title="When dialog will show")
    disregard_publishing: bool = Field(False, title="Disregard publishing")
