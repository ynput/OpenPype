from opentimelineio.opentime import to_frames


def convert_otio_range_to_frame_range(otio_range):
    start = to_frames(
        otio_range.start_time, otio_range.start_time.rate)
    end = start + to_frames(
        otio_range.duration, otio_range.duration.rate) - 1
    return start, end


def is_overlapping_otio_ranges(test_otio_range, main_otio_range, strict=False):
    test_start, test_end = convert_otio_range_to_frame_range(test_otio_range)
    main_start, main_end = convert_otio_range_to_frame_range(main_otio_range)
    covering_exp = bool(
        (test_start <= main_start) and (test_end >= main_end)
    )
    inside_exp = bool(
        (test_start >= main_start) and (test_end <= main_end)
    )
    overlaying_right_exp = bool(
        (test_start < main_end) and (test_end >= main_end)
    )
    overlaying_left_exp = bool(
        (test_end > main_start) and (test_start <= main_start)
    )

    if not strict:
        return any((
            covering_exp,
            inside_exp,
            overlaying_right_exp,
            overlaying_left_exp
        ))
    else:
        return covering_exp
