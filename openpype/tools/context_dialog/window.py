from openpype import AYON_SERVER_ENABLED

if AYON_SERVER_ENABLED:
    from ._ayon_window import ContextDialog, main
else:
    from ._openpype_window import ContextDialog, main


__all__ = (
    "ContextDialog",
    "main",
)
