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
    containerise
)

from .lib import (
    maintained_selection,
    get_extension_manifest_path,
    get_asset_settings
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
    "containerise",

    # lib
    "maintained_selection",
    "get_extension_manifest_path",
    "get_asset_settings",

    # plugin
    "AfterEffectsLoader"
]
