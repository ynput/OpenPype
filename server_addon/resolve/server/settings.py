from pydantic import Field
from ayon_server.settings import BaseSettingsModel

from .imageio import ResolveImageIOModel


class CreateShotClipModels(BaseSettingsModel):
    hierarchy: str = Field(
        "{folder}/{sequence}",
        title="Shot parent hierarchy",
        section="Shot Hierarchy And Rename Settings"
    )
    clipRename: bool = Field(
        True,
        title="Rename clips"
    )
    clipName: str = Field(
        "{track}{sequence}{shot}",
        title="Clip name template"
    )
    countFrom: int = Field(
        10,
        title="Count sequence from"
    )
    countSteps: int = Field(
        10,
        title="Stepping number"
    )

    folder: str = Field(
        "shots",
        title="{folder}",
        section="Shot Template Keywords"
    )
    episode: str = Field(
        "ep01",
        title="{episode}"
    )
    sequence: str = Field(
        "sq01",
        title="{sequence}"
    )
    track: str = Field(
        "{_track_}",
        title="{track}"
    )
    shot: str = Field(
        "sh###",
        title="{shot}"
    )

    vSyncOn: bool = Field(
        False,
        title="Enable Vertical Sync",
        section="Vertical Synchronization Of Attributes"
    )

    workfileFrameStart: int = Field(
        1001,
        title="Workfiles Start Frame",
        section="Shot Attributes"
    )
    handleStart: int = Field(
        10,
        title="Handle start (head)"
    )
    handleEnd: int = Field(
        10,
        title="Handle end (tail)"
    )


class CreatorPuginsModel(BaseSettingsModel):
    CreateShotClip: CreateShotClipModels = Field(
        default_factory=CreateShotClipModels,
        title="Create Shot Clip"
    )


class ResolveSettings(BaseSettingsModel):
    launch_openpype_menu_on_start: bool = Field(
        False, title="Launch OpenPype menu on start of Resolve"
    )
    imageio: ResolveImageIOModel = Field(
        default_factory=ResolveImageIOModel,
        title="Color Management (ImageIO)"
    )
    create: CreatorPuginsModel = Field(
        default_factory=CreatorPuginsModel,
        title="Creator plugins",
    )


DEFAULT_VALUES = {
    "launch_openpype_menu_on_start": False,
    "create": {
        "CreateShotClip": {
            "hierarchy": "{folder}/{sequence}",
            "clipRename": True,
            "clipName": "{track}{sequence}{shot}",
            "countFrom": 10,
            "countSteps": 10,
            "folder": "shots",
            "episode": "ep01",
            "sequence": "sq01",
            "track": "{_track_}",
            "shot": "sh###",
            "vSyncOn": False,
            "workfileFrameStart": 1001,
            "handleStart": 10,
            "handleEnd": 10
        }
    }
}
