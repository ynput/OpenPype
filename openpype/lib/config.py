import warnings
import functools


class ConfigDeprecatedWarning(DeprecationWarning):
    pass


def deprecated(func):
    """Mark functions as deprecated.

    It will result in a warning being emitted when the function is used.
    """

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.simplefilter("always", ConfigDeprecatedWarning)
        warnings.warn(
            (
                "Deprecated import of function '{}'."
                " Class was moved to 'openpype.lib.dateutils.{}'."
                " Please change your imports."
            ).format(func.__name__),
            category=ConfigDeprecatedWarning
        )
        return func(*args, **kwargs)
    return new_func


@deprecated
def get_datetime_data(datetime_obj=None):
    from .dateutils import get_datetime_data

    return get_datetime_data(datetime_obj)


@deprecated
def get_formatted_current_time():
    from .dateutils import get_formatted_current_time

    return get_formatted_current_time()
