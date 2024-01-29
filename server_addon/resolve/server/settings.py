from ayon_server.settings import BaseSettingsModel, SettingsField

from .imageio import ResolveImageIOModel


class CreateShotClipModels(BaseSettingsModel):
    hierarchy: str = SettingsField(
        "{folder}/{sequence}",
        title="Shot parent hierarchy",
        section="Shot Hierarchy And Rename Settings"
    )
    clipRename: bool = SettingsField(
        True,
        title="Rename clips"
    )
    clipName: str = SettingsField(
        "{track}{sequence}{shot}",
        title="Clip name template"
    )
    countFrom: int = SettingsField(
        10,
        title="Count sequence from"
    )
    countSteps: int = SettingsField(
        10,
        title="Stepping number"
    )

    folder: str = SettingsField(
        "shots",
        title="{folder}",
        section="Shot Template Keywords"
    )
    episode: str = SettingsField(
        "ep01",
        title="{episode}"
    )
    sequence: str = SettingsField(
        "sq01",
        title="{sequence}"
    )
    track: str = SettingsField(
        "{_track_}",
        title="{track}"
    )
    shot: str = SettingsField(
        "sh###",
        title="{shot}"
    )

    vSyncOn: bool = SettingsField(
        False,
        title="Enable Vertical Sync",
        section="Vertical Synchronization Of Attributes"
    )

    workfileFrameStart: int = SettingsField(
        1001,
        title="Workfiles Start Frame",
        section="Shot Attributes"
    )
    handleStart: int = SettingsField(
        10,
        title="Handle start (head)"
    )
    handleEnd: int = SettingsField(
        10,
        title="Handle end (tail)"
    )


class CreatorPuginsModel(BaseSettingsModel):
    CreateShotClip: CreateShotClipModels = SettingsField(
        default_factory=CreateShotClipModels,
        title="Create Shot Clip"
    )


class ResolveSettings(BaseSettingsModel):
    launch_openpype_menu_on_start: bool = SettingsField(
        False, title="Launch OpenPype menu on start of Resolve"
    )
    imageio: ResolveImageIOModel = SettingsField(
        default_factory=ResolveImageIOModel,
        title="Color Management (ImageIO)"
    )
    create: CreatorPuginsModel = SettingsField(
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
