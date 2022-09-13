import os
import os.path
import tempfile
import pytest
import shutil
import platform

from common.openpype_common.distribution.dependencies.dependencies import (
    FileTomlProvider,
    is_valid_toml,
    merge_tomls,
    get_full_toml,
    prepare_new_venv,
    zip_venv,
    upload_zip_venv,
    get_venv_zip_name
)


@pytest.fixture
def openpype_toml_data():
    provider = FileTomlProvider(os.path.join("..", "..", "..", "..", "..",
                                             "pyproject.toml"))
    return provider.get_toml()


@pytest.fixture
def addon_toml_to_compare_data():
    provider = FileTomlProvider(os.path.join("resources",
                                             "pyproject.toml"))
    return provider.get_toml()


@pytest.fixture
def addon_toml_to_venv_data():
    provider = FileTomlProvider(os.path.join("resources",
                                             "pyproject_clean.toml"))
    return provider.get_toml()


def test_existing_file():
    provider = FileTomlProvider(os.path.join("..", "..", "..", "..", "..",
                                             "pyproject.toml"))
    _ = provider.get_toml()


def test_not_existing_file():
    dir_name = os.path.dirname(__file__)
    provider = FileTomlProvider(os.path.join(dir_name, "pyproject.toml"))
    with pytest.raises(ValueError):
        _ = provider.get_toml()


def test_is_valid_toml(openpype_toml_data):

    assert is_valid_toml(openpype_toml_data), "Must contain all required keys"


def test_is_valid_toml_invalid(openpype_toml_data):
    openpype_toml_data.pop("tool")

    with pytest.raises(KeyError):
        is_valid_toml(openpype_toml_data)


def test_merge_tomls(openpype_toml_data, addon_toml_to_compare_data):
    result_toml = merge_tomls(openpype_toml_data, addon_toml_to_compare_data)
    _compare_resolved_tomp(result_toml)


def test_get_full_toml(openpype_toml_data):
    addon_urls = ["resources"]

    result_toml = get_full_toml(openpype_toml_data, addon_urls)
    _compare_resolved_tomp(result_toml)


def _compare_resolved_tomp(result_toml):
    res_dependencies = result_toml["tool"]["poetry"]["dependencies"]
    dep_version = res_dependencies["aiohttp"]
    assert dep_version == "3.6.*"

    dep_version = res_dependencies["new_dependency"]
    assert dep_version == "^1.0.0"

    res_dependencies = result_toml["tool"]["poetry"]["dev-dependencies"]
    dep_version = res_dependencies["new_dependency"]
    assert dep_version == "^2.0.0"

    platform_name = platform.system().lower()
    res_dependencies = (result_toml["openpype"]
                                   ["thirdparty"]
                                   ["ffmpeg"]
                                   [platform_name])
    dep_version = res_dependencies["version"]
    assert dep_version == "4.4"

    res_dependencies = (result_toml["openpype"]
                                   ["thirdparty"]
                                   ["oiio"]
                                   [platform_name])
    dep_version = res_dependencies["version"]
    assert dep_version == "2.1.0"

    res_dependencies = (result_toml["openpype"]
                                   ["thirdparty"]
                                   ["ocioconfig"])
    dep_version = res_dependencies["version"]
    assert dep_version == "1.0.0"


def test_get_venv_zip_name():
    test_file_1_path = os.path.join("resources", "pyproject.toml")

    test_file_1_name = get_venv_zip_name(test_file_1_path)
    test_file_2_name = get_venv_zip_name(test_file_1_path)

    assert test_file_1_name == test_file_2_name, \
        "Same file must result in same name"

    test_file_2_path = os.path.join("resources", "pyproject_clean.toml")
    test_file_2_name = get_venv_zip_name(test_file_2_path)

    assert test_file_1_name != test_file_2_name, \
        "Different file must result in different name"

    shutil.rmtree(tmpdir)
