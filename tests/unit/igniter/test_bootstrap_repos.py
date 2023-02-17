# -*- coding: utf-8 -*-
"""Test suite for repos bootstrapping (install)."""
import os
import sys
from collections import namedtuple
from pathlib import Path
from zipfile import ZipFile
from uuid import uuid4

import appdirs
import pytest

from igniter.bootstrap_repos import BootstrapRepos
from igniter.bootstrap_repos import OpenPypeVersion
from igniter.user_settings import OpenPypeSettingsRegistry


@pytest.fixture
def fix_bootstrap(tmp_path, pytestconfig):
    """This will fix BoostrapRepos with temp paths."""
    bs = BootstrapRepos()
    bs.live_repo_dir = pytestconfig.rootpath / 'repos'
    bs.data_dir = tmp_path
    return bs


def test_openpype_version(printer):
    """Test determination of OpenPype versions."""
    v1 = OpenPypeVersion(1, 2, 3)
    assert str(v1) == "1.2.3"

    v2 = OpenPypeVersion(1, 2, 3, prerelease="x")
    assert str(v2) == "1.2.3-x"
    assert v1 > v2

    v3 = OpenPypeVersion(1, 2, 3)
    assert str(v3) == "1.2.3"

    v4 = OpenPypeVersion(1, 2, 3, prerelease="rc.1")
    assert str(v4) == "1.2.3-rc.1"
    assert v3 > v4
    assert v1 > v4
    assert v4 < OpenPypeVersion(1, 2, 3, prerelease="rc.1")

    v5 = OpenPypeVersion(1, 2, 3, build="foo", prerelease="x")
    assert str(v5) == "1.2.3-x+foo"
    assert v4 < v5

    v6 = OpenPypeVersion(1, 2, 3, prerelease="foo")
    assert str(v6) == "1.2.3-foo"

    v7 = OpenPypeVersion(2, 0, 0)
    assert v1 < v7

    v8 = OpenPypeVersion(0, 1, 5)
    assert v8 < v7

    v9 = OpenPypeVersion(1, 2, 4)
    assert v9 > v1

    v10 = OpenPypeVersion(1, 2, 2)
    assert v10 < v1

    v11 = OpenPypeVersion(1, 2, 3, path=Path("/foo/bar"))
    assert v10 < v11

    assert v5 == v2

    sort_versions = [
        OpenPypeVersion(3, 2, 1),
        OpenPypeVersion(1, 2, 3),
        OpenPypeVersion(0, 0, 1),
        OpenPypeVersion(4, 8, 10),
        OpenPypeVersion(4, 8, 20),
        OpenPypeVersion(4, 8, 9),
        OpenPypeVersion(1, 2, 3),
        OpenPypeVersion(1, 2, 3, build="foo")
    ]
    res = sorted(sort_versions)

    assert res[0] == sort_versions[2]
    assert res[1] == sort_versions[6]
    assert res[2] == sort_versions[1]
    assert res[-1] == sort_versions[4]

    str_versions = [
        "5.5.1",
        "5.5.2-foo",
        "5.5.3-foo+strange",
        "5.5.4+staging",
        "5.5.5+staging-client",
        "5.6.3",
        "5.6.3+staging"
    ]
    res_versions = [OpenPypeVersion(version=v) for v in str_versions]
    sorted_res_versions = sorted(res_versions)

    assert str(sorted_res_versions[0]) == str_versions[0]
    assert str(sorted_res_versions[-1]) == str_versions[5]

    with pytest.raises(TypeError):
        _ = OpenPypeVersion()

    with pytest.raises(ValueError):
        _ = OpenPypeVersion(version="booobaa")

    v11 = OpenPypeVersion(version="4.6.7-foo")
    assert v11.major == 4
    assert v11.minor == 6
    assert v11.patch == 7
    assert v11.prerelease == "foo"


def test_get_main_version():
    ver = OpenPypeVersion(1, 2, 3, prerelease="foo")
    assert ver.get_main_version() == "1.2.3"


def test_get_version_path_from_list():
    versions = [
        OpenPypeVersion(1, 2, 3, path=Path('/foo/bar')),
        OpenPypeVersion(3, 4, 5, path=Path("/bar/baz")),
        OpenPypeVersion(6, 7, 8, prerelease="x", path=Path("boo/goo"))
    ]
    path = BootstrapRepos.get_version_path_from_list(
        "3.4.5", versions)

    assert path == Path("/bar/baz")


def test_search_string_for_openpype_version(printer):
    strings = [
        ("3.0.1", True),
        ("foo-3.0", False),
        ("foo-3.0.1", True),
        ("3", False),
        ("foo-3.0.1-client-staging", True),
        ("foo-3.0.1-bar-baz", True)
    ]
    for ver_string in strings:
        printer(f"testing {ver_string[0]} should be {ver_string[1]}")
        assert isinstance(
            OpenPypeVersion.version_in_str(ver_string[0]),
            OpenPypeVersion if ver_string[1] else type(None)
        )

@pytest.mark.slow
def test_install_live_repos(fix_bootstrap, printer, monkeypatch, pytestconfig):
    monkeypatch.setenv("OPENPYPE_ROOT", pytestconfig.rootpath.as_posix())
    monkeypatch.setenv("OPENPYPE_DATABASE_NAME", str(uuid4()))
    openpype_version = fix_bootstrap.create_version_from_live_code()
    sep = os.path.sep
    expected_paths = [
        f"{openpype_version.path}"
    ]
    printer("testing zip creation")
    assert os.path.exists(openpype_version.path), "zip archive was not created"
    fix_bootstrap.add_paths_from_archive(openpype_version.path)
    for ep in expected_paths:
        assert ep in sys.path, f"{ep} not set correctly"

    printer("testing openpype imported")
    try:
        del sys.modules["openpype"]
    except KeyError:
        # wasn't imported before
        pass
    import openpype  # noqa: F401

    # test if openpype is imported from specific location in zip
    assert "openpype" in sys.modules.keys(), "OpenPype not imported"
    assert sys.modules["openpype"].__file__ == \
        f"{openpype_version.path}{sep}openpype{sep}__init__.py"


def test_find_openpype(fix_bootstrap, tmp_path_factory, monkeypatch, printer):
    test_openpype = namedtuple("OpenPype", "prefix version suffix type valid")

    test_versions_1 = [
        test_openpype(prefix="foo-v", version="5.5.1",
                      suffix=".zip", type="zip", valid=False),
        test_openpype(prefix="bar-v", version="5.5.2-rc.1",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="baz-v", version="5.5.3-foo-strange",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="bum-v", version="5.5.4+staging",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="zum-v", version="5.5.5-foo+staging",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="fam-v", version="5.6.3",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="foo-v", version="5.6.3+staging",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="fim-v", version="5.6.3",
                      suffix=".zip", type="zip", valid=False),
        test_openpype(prefix="foo-v", version="5.6.4",
                      suffix=".txt", type="txt", valid=False),
        test_openpype(prefix="foo-v", version="5.7.1",
                      suffix="", type="dir", valid=False),
    ]

    test_versions_2 = [
        test_openpype(prefix="foo-v", version="10.0.0",
                      suffix=".txt", type="txt", valid=False),
        test_openpype(prefix="lom-v", version="7.2.6",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="bom-v", version="7.2.7-rc.3",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="woo-v", version="7.2.8-foo-strange",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="loo-v", version="7.2.10-foo+staging",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="kok-v", version="7.0.1",
                      suffix=".zip", type="zip", valid=True)
    ]

    test_versions_3 = [
        test_openpype(prefix="foo-v", version="3.0.0",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="goo-v", version="3.0.1",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="hoo-v", version="4.1.0",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="foo-v", version="4.1.2",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="foo-v", version="3.0.1-foo",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="foo-v", version="3.0.1-foo-strange",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="foo-v", version="3.0.1+staging",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="foo-v", version="3.0.1-foo+staging",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="foo-v", version="3.2.0",
                      suffix=".zip", type="zip", valid=True)
    ]

    test_versions_4 = [
        test_openpype(prefix="foo-v", version="10.0.0",
                      suffix="", type="dir", valid=True),
        test_openpype(prefix="lom-v", version="11.2.6",
                      suffix=".zip", type="dir", valid=False),
        test_openpype(prefix="bom-v", version="7.2.7-foo",
                      suffix=".zip", type="zip", valid=True),
        test_openpype(prefix="woo-v", version="7.2.8-foo-strange",
                      suffix=".zip", type="txt", valid=False)
    ]

    def _create_invalid_zip(path: Path):
        with ZipFile(path, "w") as zf:
            zf.writestr("test.foo", "test")

    def _create_valid_zip(path: Path, version: str):
        with ZipFile(path, "w") as zf:
            zf.writestr(
                "openpype/version.py", f"__version__ = '{version}'\n\n")

    def _create_invalid_dir(path: Path):
        path.mkdir(parents=True, exist_ok=True)
        with open(path / "invalid", "w") as fp:
            fp.write("invalid")

    def _create_valid_dir(path: Path, version: str):
        openpype_path = path / "openpype"
        version_path = openpype_path / "version.py"
        openpype_path.mkdir(parents=True, exist_ok=True)
        with open(version_path, "w") as fp:
            fp.write(f"__version__ = '{version}'\n\n")

    def _build_test_item(path, item):
        test_path = path / "{}{}{}".format(item.prefix,
                                           item.version,
                                           item.suffix)
        if item.type == "zip":
            if item.valid:
                _create_valid_zip(test_path, item.version)
            else:
                _create_invalid_zip(test_path)
        elif item.type == "dir":
            if item.valid:
                _create_valid_dir(test_path, item.version)
            else:
                _create_invalid_dir(test_path)
        else:
            with open(test_path, "w") as fp:
                fp.write("foo")

    # in OPENPYPE_PATH
    e_path = tmp_path_factory.mktemp("environ")

    # create files and directories for test
    for test_file in test_versions_1:
        _build_test_item(e_path, test_file)

    # in openPypePath registry
    p_path = tmp_path_factory.mktemp("openPypePath")
    for test_file in test_versions_2:
        _build_test_item(p_path, test_file)

    # in data dir
    d_path = tmp_path_factory.mktemp("dataPath")
    for test_file in test_versions_2:
        _build_test_item(d_path, test_file)

    # in provided path
    g_path = tmp_path_factory.mktemp("providedPath")
    for test_file in test_versions_3:
        _build_test_item(g_path, test_file)

    # dir vs zip preference
    dir_path = tmp_path_factory.mktemp("dirZipPath")
    for test_file in test_versions_4:
        _build_test_item(dir_path, test_file)

    printer("testing finding OpenPype in given path ...")
    result = fix_bootstrap.find_openpype(g_path, include_zips=True)
    # we should have results as file were created
    assert result is not None, "no OpenPype version found"
    # latest item in `result` should be latest version found.
    expected_path = Path(
        g_path / "{}{}{}".format(
            test_versions_3[3].prefix,
            test_versions_3[3].version,
            test_versions_3[3].suffix
        )
    )
    assert result, "nothing found"
    assert result[-1].path == expected_path, ("not a latest version of "
                                              "OpenPype 3")

    printer("testing finding OpenPype in OPENPYPE_PATH ...")
    monkeypatch.setenv("OPENPYPE_PATH", e_path.as_posix())
    result = fix_bootstrap.find_openpype(include_zips=True)
    # we should have results as file were created
    assert result is not None, "no OpenPype version found"
    # latest item in `result` should be latest version found.
    expected_path = Path(
        e_path / "{}{}{}".format(
            test_versions_1[5].prefix,
            test_versions_1[5].version,
            test_versions_1[5].suffix
        )
    )
    assert result, "nothing found"
    assert result[-1].path == expected_path, ("not a latest version of "
                                              "OpenPype 1")

    monkeypatch.delenv("OPENPYPE_PATH", raising=False)

    printer("testing finding OpenPype in user data dir ...")

    # mock appdirs user_data_dir
    def mock_user_data_dir(*args, **kwargs):
        """Mock local app data dir."""
        return d_path.as_posix()

    monkeypatch.setattr(appdirs, "user_data_dir", mock_user_data_dir)
    fix_bootstrap.registry = OpenPypeSettingsRegistry()
    fix_bootstrap.registry.set_item("openPypePath", d_path.as_posix())

    result = fix_bootstrap.find_openpype(include_zips=True)
    # we should have results as file were created
    assert result is not None, "no OpenPype version found"
    # latest item in `result` should be the latest version found.
    # this will be `7.2.10-foo+staging` even with *staging* in since we've
    # dropped the logic to handle staging separately and in alphabetical
    # sorting it is after `strange`.
    expected_path = Path(
        d_path / "{}{}{}".format(
            test_versions_2[4].prefix,
            test_versions_2[4].version,
            test_versions_2[4].suffix
        )
    )
    assert result, "nothing found"
    assert result[-1].path == expected_path, ("not a latest version of "
                                              "OpenPype 2")

    printer("testing finding OpenPype zip/dir precedence ...")
    result = fix_bootstrap.find_openpype(dir_path, include_zips=True)
    assert result is not None, "no OpenPype versions found"
    expected_path = Path(
        dir_path / "{}{}{}".format(
            test_versions_4[0].prefix,
            test_versions_4[0].version,
            test_versions_4[0].suffix
        )
    )
    assert result[-1].path == expected_path, ("not a latest version of "
                                              "OpenPype 4")
