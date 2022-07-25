"""Content was moved to 'openpype.pipeline.publish.publish_plugins'.

Please change your imports as soon as possible.

File will be probably removed in OpenPype 3.14.*
"""

import warnings
from openpype.pipeline.publish import (
    AbstractMetaInstancePlugin,
    AbstractMetaContextPlugin
)


class MetaPluginsDeprecated(DeprecationWarning):
    pass


warnings.simplefilter("always", MetaPluginsDeprecated)
warnings.warn(
    (
        "Content of 'abstract_metaplugins' was moved."
        "\nUsing deprecated source of 'abstract_metaplugins'. Content was"
        " moved to 'openpype.pipeline.publish.publish_plugins'."
        " Please change your imports as soon as possible."
    ),
    category=MetaPluginsDeprecated,
    stacklevel=4
)


__all__ = (
    "AbstractMetaInstancePlugin",
    "AbstractMetaContextPlugin",
)
