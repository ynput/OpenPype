# -*- coding: utf-8 -*-
"""Content was moved to 'openpype.pipeline.farm.abstract_collect_render'.

Please change your imports as soon as possible.

File will be probably removed in OpenPype 3.14.*
"""

import warnings
from openpype.pipeline.publish import AbstractCollectRender, RenderInstance


class CollectRenderDeprecated(DeprecationWarning):
    pass


warnings.simplefilter("always", CollectRenderDeprecated)
warnings.warn(
    (
        "Content of 'abstract_collect_render' was moved."
        "\nUsing deprecated source of 'abstract_collect_render'. Content was"
        " move to 'openpype.pipeline.farm.abstract_collect_render'."
        " Please change your imports as soon as possible."
    ),
    category=CollectRenderDeprecated,
    stacklevel=4
)


__all__ = (
    "AbstractCollectRender",
    "RenderInstance"
)
