# -*- coding: utf-8 -*-
"""Test suite for delivery functions."""
from openpype.lib.delivery import collect_frames


def test_collect_frames_multi_sequence():
    files = ["Asset_renderCompositingMain_v001.0000.png",
             "Asset_renderCompositingMain_v001.0001.png",
             "Asset_renderCompositingMain_v001.0002.png"]
    ret = collect_frames(files)

    expected = {
        "Asset_renderCompositingMain_v001.0000.png": "0000",
        "Asset_renderCompositingMain_v001.0001.png": "0001",
        "Asset_renderCompositingMain_v001.0002.png": "0002"
    }

    print(ret)
    assert ret == expected, "Not matching"


def test_collect_frames_multi_sequence_different_format():
    files = ["Asset.v001.renderCompositingMain.0000.png",
             "Asset.v001.renderCompositingMain.0001.png",
             "Asset.v001.renderCompositingMain.0002.png"]
    ret = collect_frames(files)

    expected = {
        "Asset.v001.renderCompositingMain.0000.png": "0000",
        "Asset.v001.renderCompositingMain.0001.png": "0001",
        "Asset.v001.renderCompositingMain.0002.png": "0002"
    }

    print(ret)
    assert ret == expected, "Not matching"


def test_collect_frames_single_sequence():
    files = ["Asset_renderCompositingMain_v001.0000.png"]
    ret = collect_frames(files)

    expected = {
        "Asset_renderCompositingMain_v001.0000.png": "0000"
    }

    print(ret)
    assert ret == expected, "Not matching"


def test_collect_frames_single_sequence_full_path():
    files = ['C:/test_project/assets/locations/Town/work/compositing\\renders\\aftereffects\\test_project_TestAsset_compositing_v001\\TestAsset_renderCompositingMain_v001.mov']  # noqa: E501
    ret = collect_frames(files)

    expected = {
        'C:/test_project/assets/locations/Town/work/compositing\\renders\\aftereffects\\test_project_TestAsset_compositing_v001\\TestAsset_renderCompositingMain_v001.mov': None  # noqa: E501
    }

    print(ret)
    assert ret == expected, "Not matching"


def test_collect_frames_single_sequence_different_format():
    files = ["Asset.v001.renderCompositingMain_0000.png"]
    ret = collect_frames(files)

    expected = {
        "Asset.v001.renderCompositingMain_0000.png": "0000"
    }

    print(ret)
    assert ret == expected, "Not matching"


def test_collect_frames_single_sequence_withhout_version():
    files = ["pngv001.renderCompositingMain_0000.png"]
    ret = collect_frames(files)

    expected = {
        "pngv001.renderCompositingMain_0000.png": "0000"
    }

    print(ret)
    assert ret == expected, "Not matching"


def test_collect_frames_single_sequence_as_dict():
    files = {"Asset_renderCompositingMain_v001.0000.png"}
    ret = collect_frames(files)

    expected = {
        "Asset_renderCompositingMain_v001.0000.png": "0000"
    }

    print(ret)
    assert ret == expected, "Not matching"


def test_collect_frames_single_file():
    files = {"Asset_renderCompositingMain_v001.png"}
    ret = collect_frames(files)

    expected = {
        "Asset_renderCompositingMain_v001.png": None
    }

    print(ret)
    assert ret == expected, "Not matching"

