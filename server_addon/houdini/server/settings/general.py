from pydantic import Field
from ayon_server.settings import BaseSettingsModel


class GeneralSettingsModel(BaseSettingsModel):
    add_self_publish_button: bool = Field(
        False,
        title="Add Self Publish Button"
    )


DEFAULT_GENERAL_SETTINGS = {
    "add_self_publish_button": False
}
