"""Public API

Anything that isn't defined here is INTERNAL and unreliable for external use.

"""

from .ws_stub import (
    get_stub,
)

from .pipeline import (
    AfterEffectsHost,
    ls,
    containerise
)

from .lib import (
    maintained_selection,
    get_extension_manifest_path,
    get_asset_settings,
    set_settings
)

from .plugin import (
    AfterEffectsLoader
)


__all__ = [
    # ws_stub
    "get_stub",

    # pipeline
    "ls",
    "containerise",

    # lib
    "maintained_selection",
    "get_extension_manifest_path",
    "get_asset_settings",
    "set_settings",

    # plugin
    "AfterEffectsLoader"
]
