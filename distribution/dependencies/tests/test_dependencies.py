import os
import os.path

import pytest

from distribution.dependencies.dependencies import (
    FileTomlProvider,
    is_valid_toml,
    merge_tomls
)


@pytest.fixture
def openpype_toml_data():
    provider = FileTomlProvider(os.path.join("..", "..", "..",
                                             "pyproject.toml"))
    return provider.get_toml()


@pytest.fixture
def addon_toml_data():
    provider = FileTomlProvider(os.path.join("resources", "pyproject.toml"))
    return provider.get_toml()


def test_existing_file():
    provider = FileTomlProvider(os.path.join("..", "..", "..",
                                             "pyproject.toml"))
    toml = provider.get_toml()


def test_not_existing_file():
    dir_name = os.path.dirname(__file__)
    provider = FileTomlProvider(os.path.join(dir_name, "pyproject.toml"))
    with pytest.raises(ValueError):
        toml = provider.get_toml()


def test_is_valid_toml(openpype_toml_data):

    assert is_valid_toml(openpype_toml_data), "Must contain all required keys"


def test_is_valid_toml_invalid(openpype_toml_data):
    openpype_toml_data.pop("tool")

    with pytest.raises(KeyError):
        is_valid_toml(openpype_toml_data)


def test_merge_tomls(openpype_toml_data, addon_toml_data):
    result_toml = merge_tomls(openpype_toml_data, addon_toml_data)
    res_dependencies = result_toml["tool"]["poetry"]["dependencies"]
    dep_version = res_dependencies["aiohttp"]
    assert dep_version == "3.6.*"

    dep_version = res_dependencies["new_dependency"]
    assert dep_version == "^1.0.0"

    res_dependencies = result_toml["tool"]["poetry"]["dev-dependencies"]
    dep_version = res_dependencies["new_dependency"]
    assert dep_version == "^2.0.0"
