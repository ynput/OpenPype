import os
import os.path
import tempfile
import pytest
import shutil
import platform

from common.openpype_common.distribution.dependencies.dependencies import (
    FileTomlProvider,
    ServerTomlProvider,
    is_valid_toml,
    merge_tomls,
    get_full_toml,
    prepare_new_venv,
    zip_venv,
    get_venv_zip_name,
    lock_to_toml_data,
    remove_existing_from_venv
)

ROOT_FOLDER = os.path.abspath(os.path.join("..", "..", "..", "..", ".."))
PURGE_TMP = True


@pytest.fixture
def openpype_toml_data():
    provider = FileTomlProvider(os.path.join(ROOT_FOLDER,
                                             "pyproject.toml"))
    return provider.get_toml()


@pytest.fixture
def addon_toml_to_compare_data():
    """Test file contains dummy data to test version compare"""
    provider = FileTomlProvider(os.path.join("resources",
                                             "pyproject.toml"))
    return provider.get_toml()


@pytest.fixture
def addon_toml_to_venv_data():
    """Test file contains 'close to live' toml for single addon."""
    provider = FileTomlProvider(os.path.join("resources",
                                             "pyproject_clean.toml"))
    return provider.get_toml()


@pytest.fixture(scope="module")
def tmpdir():
    tmpdir = tempfile.mkdtemp(prefix="openpype_test_")

    yield tmpdir

    if PURGE_TMP:
        try:
            shutil.rmtree(tmpdir)
        except PermissionError:
            print(f"Couldn't delete {tmpdir}")


def test_existing_file():
    provider = FileTomlProvider(os.path.join(ROOT_FOLDER,
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
    with open(os.path.join("resources", "pyproject.toml")) as fp:
        addon_tomls = [fp.read()]

    result_toml = get_full_toml(openpype_toml_data, addon_tomls)
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

    with pytest.raises(FileNotFoundError):
        get_venv_zip_name(test_file_1_path + ".ntext")


def test_lock_to_toml_data():
    lock_file_path = os.path.join("resources", "poetry.lock")

    toml_data = lock_to_toml_data(lock_file_path)

    assert (toml_data["tool"]["poetry"]["dependencies"]["acre"] == "1.0.0",
            "Wrong version, must be '1.0.0'")

    assert is_valid_toml(toml_data), "Must contain all required keys"


def test_prepare_new_venv(addon_toml_to_venv_data, tmpdir):
    """Creates zip of simple venv from mock addon pyproject data"""
    print(f"Creating new venv in {tmpdir}")
    return_code = prepare_new_venv(addon_toml_to_venv_data, tmpdir)

    assert return_code != 1, "Prepare of new venv failed"

    inst_lib = os.path.join(tmpdir, '.venv', 'Lib', 'site-packages', 'aiohttp')
    assert os.path.exists(inst_lib), "aiohttp should be installed"


def test_remove_existing_from_venv(tmpdir):
    """New venv shouldn't contain libraries already in build venv."""
    base_venv_path = os.path.join(ROOT_FOLDER, ".venv")
    addon_venv_path = os.path.join(tmpdir, ".venv")

    assert os.path.exists(base_venv_path), "Base venv must exist"
    assert os.path.exists(addon_venv_path), "Addon venv must exist"

    removed = remove_existing_from_venv(base_venv_path, addon_venv_path)

    assert "aiohttp" in removed, "aiohttp is in base, should be removed"


def test_zip_venv(tmpdir):
    zip_file_name = get_venv_zip_name(os.path.join(tmpdir, "poetry.lock"))
    venv_zip_path = os.path.join(tmpdir, zip_file_name)
    zip_venv(os.path.join(tmpdir, ".venv"),
             venv_zip_path)

    assert os.path.exists(venv_zip_path)


def test_ServerTomlProvider():
    # TODO switch to mocks without test server
    server_endpoint = "https://34e99f0f-f987-4715-95e6-d2d88caa7586.mock.pstmn.io/get_addons_tomls"  # noqa
    tomls = ServerTomlProvider(server_endpoint).get_tomls()

    assert len(tomls) == 1, "One addon should have dependencies"

    assert (tomls[0]["tool"]["poetry"]["dependencies"]["python"] == "^3.10",
            "Missing dependency")
