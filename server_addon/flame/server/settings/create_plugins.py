from pydantic import Field
from ayon_server.settings import BaseSettingsModel


class CreateShotClipModel(BaseSettingsModel):
    hierarchy: str = Field(
        "shot",
        title="Shot parent hierarchy",
        section="Shot Hierarchy And Rename Settings"
    )
    useShotName: bool = Field(
        True,
        title="Use Shot Name",
    )
    clipRename: bool = Field(
        False,
        title="Rename clips",
    )
    clipName: str = Field(
        "{sequence}{shot}",
        title="Clip name template"
    )
    segmentIndex: bool = Field(
        True,
        title="Accept segment order"
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
        "a",
        title="{sequence}"
    )
    track: str = Field(
        "{_track_}",
        title="{track}"
    )
    shot: str = Field(
        "####",
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
    includeHandles: bool = Field(
        False,
        title="Enable handles including"
    )
    retimedHandles: bool = Field(
        True,
        title="Enable retimed handles"
    )
    retimedFramerange: bool = Field(
        True,
        title="Enable retimed shot frameranges"
    )


class CreatePuginsModel(BaseSettingsModel):
    CreateShotClip: CreateShotClipModel = Field(
        default_factory=CreateShotClipModel,
        title="Create Shot Clip"
    )


DEFAULT_CREATE_SETTINGS = {
    "CreateShotClip": {
        "hierarchy": "{folder}/{sequence}",
        "useShotName": True,
        "clipRename": False,
        "clipName": "{sequence}{shot}",
        "segmentIndex": True,
        "countFrom": 10,
        "countSteps": 10,
        "folder": "shots",
        "episode": "ep01",
        "sequence": "a",
        "track": "{_track_}",
        "shot": "####",
        "vSyncOn": False,
        "workfileFrameStart": 1001,
        "handleStart": 5,
        "handleEnd": 5,
        "includeHandles": False,
        "retimedHandles": True,
        "retimedFramerange": True
    }
}
