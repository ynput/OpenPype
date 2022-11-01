"""Public API

Anything that isn't defined here is INTERNAL and unreliable for external use.

"""

from .launch_logic import (
    get_stub,
    stub,
)

from .pipeline import (
    AfterEffectsHost,
    ls,
    get_asset_settings,
    containerise
)

from .lib import (
    maintained_selection,
    get_extension_manifest_path
)

from .plugin import (
    AfterEffectsLoader
)


__all__ = [
    # launch_logic
    "get_stub",
    "stub",

    # pipeline
    "ls",
    "get_asset_settings",
    "containerise",

    # lib
    "maintained_selection",
    "get_extension_manifest_path",

    # plugin
    "AfterEffectsLoader"
]
