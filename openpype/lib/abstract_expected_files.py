# -*- coding: utf-8 -*-
"""Content was moved to 'openpype.pipeline.publish.abstract_expected_files'.

Please change your imports as soon as possible.

File will be probably removed in OpenPype 3.14.*
"""

import warnings
from openpype.pipeline.publish import ExpectedFiles


class ExpectedFilesDeprecated(DeprecationWarning):
    pass


warnings.simplefilter("always", ExpectedFilesDeprecated)
warnings.warn(
    (
        "Content of 'abstract_expected_files' was moved."
        "\nUsing deprecated source of 'abstract_expected_files'. Content was"
        " move to 'openpype.pipeline.publish.abstract_expected_files'."
        " Please change your imports as soon as possible."
    ),
    category=ExpectedFilesDeprecated,
    stacklevel=4
)


__all__ = (
    "ExpectedFiles",
)
