import warnings
import functools


def editorial_deprecated(func):
    """Mark functions as deprecated.

    It will result in a warning being emitted when the function is used.
    """

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.warn(
            (
                "Call to deprecated function '{}'."
                " Function was moved to 'openpype.pipeline.editorial'."
            ).format(func.__name__),
            category=DeprecationWarning,
            stacklevel=2
        )
        return func(*args, **kwargs)
    return new_func


@editorial_deprecated
def otio_range_to_frame_range(*args, **kwargs):
    from openpype.pipeline.editorial import otio_range_to_frame_range

    return otio_range_to_frame_range(*args, **kwargs)


@editorial_deprecated
def otio_range_with_handles(*args, **kwargs):
    from openpype.pipeline.editorial import otio_range_with_handles

    return otio_range_with_handles(*args, **kwargs)


@editorial_deprecated
def is_overlapping_otio_ranges(*args, **kwargs):
    from openpype.pipeline.editorial import is_overlapping_otio_ranges

    return is_overlapping_otio_ranges(*args, **kwargs)


@editorial_deprecated
def convert_to_padded_path(*args, **kwargs):
    from openpype.pipeline.editorial import convert_to_padded_path

    return convert_to_padded_path(*args, **kwargs)


@editorial_deprecated
def trim_media_range(*args, **kwargs):
    from openpype.pipeline.editorial import trim_media_range

    return trim_media_range(*args, **kwargs)


@editorial_deprecated
def range_from_frames(*args, **kwargs):
    from openpype.pipeline.editorial import range_from_frames

    return range_from_frames(*args, **kwargs)


@editorial_deprecated
def frames_to_secons(*args, **kwargs):
    from openpype.pipeline.editorial import frames_to_seconds

    return frames_to_seconds(*args, **kwargs)


@editorial_deprecated
def frames_to_timecode(*args, **kwargs):
    from openpype.pipeline.editorial import frames_to_timecode

    return frames_to_timecode(*args, **kwargs)


@editorial_deprecated
def make_sequence_collection(*args, **kwargs):
    from openpype.pipeline.editorial import make_sequence_collection

    return make_sequence_collection(*args, **kwargs)


@editorial_deprecated
def get_media_range_with_retimes(*args, **kwargs):
    from openpype.pipeline.editorial import get_media_range_with_retimes

    return get_media_range_with_retimes(*args, **kwargs)
