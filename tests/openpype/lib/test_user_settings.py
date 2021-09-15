# -*- coding: utf-8 -*-
"""Test suite for User Settings."""
import pytest
from igniter.user_settings import (
    IniSettingRegistry,
    JSONSettingRegistry,
    OpenPypeSecureRegistry
)
from uuid import uuid4
import configparser


@pytest.fixture
def secure_registry():
    name = "pypetest_{}".format(str(uuid4()))
    r = OpenPypeSecureRegistry(name)
    yield r


@pytest.fixture
def json_registry(tmpdir):
    name = "pypetest_{}".format(str(uuid4()))
    r = JSONSettingRegistry(name, tmpdir)
    yield r


@pytest.fixture
def ini_registry(tmpdir):
    name = "pypetest_{}".format(str(uuid4()))
    r = IniSettingRegistry(name, tmpdir)
    yield r


def test_keyring(secure_registry):
    secure_registry.set_item("item1", "foo")
    secure_registry.set_item("item2", "bar")
    result1 = secure_registry.get_item("item1")
    result2 = secure_registry.get_item("item2")

    assert result1 == "foo"
    assert result2 == "bar"

    secure_registry.delete_item("item1")
    secure_registry.delete_item("item2")

    with pytest.raises(ValueError):
        secure_registry.get_item("item1")
        secure_registry.get_item("item2")


def test_ini_registry(ini_registry):
    ini_registry.set_item("test1", "bar")
    ini_registry.set_item_section("TEST", "test2", "foo")
    ini_registry.set_item_section("TEST", "test3", "baz")
    ini_registry["woo"] = 1

    result1 = ini_registry.get_item("test1")
    result2 = ini_registry.get_item_from_section("TEST", "test2")
    result3 = ini_registry.get_item_from_section("TEST", "test3")
    result4 = ini_registry["woo"]

    assert result1 == "bar"
    assert result2 == "foo"
    assert result3 == "baz"
    assert result4 == "1"

    with pytest.raises(ValueError):
        ini_registry.get_item("xxx")

    with pytest.raises(ValueError):
        ini_registry.get_item_from_section("FFF", "yyy")

    ini_registry.delete_item("test1")
    with pytest.raises(ValueError):
        ini_registry.get_item("test1")

    ini_registry.delete_item_from_section("TEST", "test2")
    with pytest.raises(ValueError):
        ini_registry.get_item_from_section("TEST", "test2")

    ini_registry.delete_item_from_section("TEST", "test3")
    with pytest.raises(ValueError):
        ini_registry.get_item_from_section("TEST", "test3")

    del ini_registry["woo"]
    with pytest.raises(ValueError):
        ini_registry.get_item("woo")

    # ensure TEST section is also deleted
    cfg = configparser.ConfigParser()
    cfg.read(ini_registry._registry_file)
    assert "TEST" not in cfg.sections()

    with pytest.raises(ValueError):
        ini_registry.delete_item("ooo")

    with pytest.raises(ValueError):
        ini_registry.delete_item_from_section("XXX", "UUU")


def test_json_registry(json_registry):
    json_registry.set_item("foo", "bar")
    json_registry.set_item("baz", {"a": 1, "b": "c"})
    json_registry["woo"] = 1

    result1 = json_registry.get_item("foo")
    result2 = json_registry.get_item("baz")
    result3 = json_registry["woo"]

    assert result1 == "bar"
    assert result2["a"] == 1
    assert result2["b"] == "c"
    assert result3 == 1

    with pytest.raises(ValueError):
        json_registry.get_item("zoo")

    json_registry.delete_item("foo")

    with pytest.raises(ValueError):
        json_registry.get_item("foo")

    del json_registry["woo"]
    with pytest.raises(ValueError):
        json_registry.get_item("woo")
