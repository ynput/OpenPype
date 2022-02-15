from openpype.plugins.publish.extract_review import ExtractReview


def test_fix_ffmpeg_full_args_filters():
    """Tests because of wrong resolution of audio filters."""
    plugin = ExtractReview()
    output_arg = "c:/test-afbdc"
    ret = plugin.ffmpeg_full_args([], [], [], [output_arg])
    assert len(ret) == 2, "Parsed wrong"
    assert ret[-1] == output_arg

    ret = plugin.ffmpeg_full_args([], [], ["adeclick"], [output_arg])
    assert len(ret) == 4, "Parsed wrong"
    assert ret[-1] == output_arg
    assert ret[-2] == '"adeclick"'
    assert ret[-3] == "-filter:a"

    ret = plugin.ffmpeg_full_args([], [], [], [output_arg, "-af adeclick"])
    assert len(ret) == 4, "Parsed wrong"
    assert ret[-1] == output_arg
    assert ret[-2] == '"adeclick"'
    assert ret[-3] == "-filter:a"

    ret = plugin.ffmpeg_full_args([], [], ["adeclick"],
                                  [output_arg, "-af adeclick"])
    assert len(ret) == 4, "Parsed wrong"
    assert ret[-1] == output_arg
    assert ret[-2] == '"adeclick,adeclick"'  # TODO fix this duplication
    assert ret[-3] == "-filter:a"
