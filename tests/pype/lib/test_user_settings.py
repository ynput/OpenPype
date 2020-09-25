import pytest
from pype.lib import IniSettingRegistry
from pype.lib import JSONSettingRegistry
from pype.lib import PypeSettingsRegistry
from uuid import uuid4
import configparser


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


def test_keyring(json_registry, printer):
    printer("testing get/set")
    service = json_registry._name
    json_registry.set_secure_item("item1", "foo")
    json_registry.set_secure_item("item2", "bar")
    result1 = json_registry.get_secure_item("item1")
    result2 = json_registry.get_secure_item("item2")

    assert result1 == "foo"
    assert result2 == "bar"

    printer(f"testing delete from {service}")

    json_registry.delete_secure_item("item1")
    json_registry.delete_secure_item("item2")

    with pytest.raises(ValueError):
        json_registry.get_secure_item("item1")
        json_registry.get_secure_item("item2")


def test_ini_registry(ini_registry, printer):
    printer("testing get/set")
    ini_registry.set_item("test1", "bar")
    ini_registry.set_item_section("TEST", "test2", "foo")
    ini_registry.set_item_section("TEST", "test3", "baz")

    result1 = ini_registry.get_item("test1")
    result2 = ini_registry.get_item_from_section("TEST", "test2")
    result3 = ini_registry.get_item_from_section("TEST", "test3")

    assert result1 == "bar"
    assert result2 == "foo"
    assert result3 == "baz"

    printer("test non-existent value")
    with pytest.raises(ValueError):
        ini_registry.get_item("xxx")

    with pytest.raises(ValueError):
        ini_registry.get_item_from_section("FFF", "yyy")

    printer("test deleting")

    ini_registry.delete_item("test1")
    with pytest.raises(ValueError):
        ini_registry.get_item("test1")

    ini_registry.delete_item_from_section("TEST", "test2")
    with pytest.raises(ValueError):
        ini_registry.get_item_from_section("TEST", "test2")

    ini_registry.delete_item_from_section("TEST", "test3")
    with pytest.raises(ValueError):
        ini_registry.get_item_from_section("TEST", "test3")

    # ensure TEST section is also deleted
    cfg = configparser.ConfigParser()
    cfg.read(ini_registry._registry_file)
    assert "TEST" not in cfg.sections()

    with pytest.raises(ValueError):
        ini_registry.delete_item("ooo")

    with pytest.raises(ValueError):
        ini_registry.delete_item_from_section("XXX", "UUU")
