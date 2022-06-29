"""Code related to project Anatomy was moved
to 'openpype.pipeline.anatomy' please change your imports as soon as
possible. File will be probably removed in OpenPype 3.14.*
"""

import warnings
import functools


class AnatomyDeprecatedWarning(DeprecationWarning):
    pass


def anatomy_deprecated(func):
    """Mark functions as deprecated.

    It will result in a warning being emitted when the function is used.
    """

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.simplefilter("always", AnatomyDeprecatedWarning)
        warnings.warn(
            (
                "Deprecated import of 'Anatomy'."
                " Class was moved to 'openpype.pipeline.anatomy'."
                " Please change your imports of Anatomy in codebase."
            ),
            category=AnatomyDeprecatedWarning
        )
        return func(*args, **kwargs)
    return new_func


@anatomy_deprecated
def Anatomy(*args, **kwargs):
    from openpype.pipeline.anatomy import Anatomy
    return Anatomy(*args, **kwargs)
