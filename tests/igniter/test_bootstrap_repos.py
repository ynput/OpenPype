# -*- coding: utf-8 -*-
"""Test suite for repos bootstrapping (install)."""
import os
import sys
from collections import namedtuple
from pathlib import Path
from zipfile import ZipFile

import appdirs
import pytest

from igniter.bootstrap_repos import BootstrapRepos
from igniter.bootstrap_repos import PypeVersion
from pype.lib import PypeSettingsRegistry


@pytest.fixture
def fix_bootstrap(tmp_path, pytestconfig):
    bs = BootstrapRepos()
    bs.live_repo_dir = pytestconfig.rootpath / 'repos'
    bs.data_dir = tmp_path
    return bs


def test_pype_version():
    v1 = PypeVersion(1, 2, 3)
    assert str(v1) == "1.2.3"

    v2 = PypeVersion(1, 2, 3, client="x")
    assert str(v2) == "1.2.3-x"
    assert v1 < v2

    v3 = PypeVersion(1, 2, 3, variant="staging")
    assert str(v3) == "1.2.3-staging"

    v4 = PypeVersion(1, 2, 3, variant="staging", client="client")
    assert str(v4) == "1.2.3-client-staging"
    assert v3 < v4
    assert v1 < v4

    v5 = PypeVersion(1, 2, 3, variant="foo", client="x")
    assert str(v5) == "1.2.3-x"
    assert v4 < v5

    v6 = PypeVersion(1, 2, 3, variant="foo")
    assert str(v6) == "1.2.3"

    v7 = PypeVersion(2, 0, 0)
    assert v1 < v7

    v8 = PypeVersion(0, 1, 5)
    assert v8 < v7

    v9 = PypeVersion(1, 2, 4)
    assert v9 > v1

    v10 = PypeVersion(1, 2, 2)
    assert v10 < v1

    v11 = PypeVersion(1, 2, 3, path=Path("/foo/bar"))
    assert v10 < v11

    assert v5 == v2

    sort_versions = [
        PypeVersion(3, 2, 1),
        PypeVersion(1, 2, 3),
        PypeVersion(0, 0, 1),
        PypeVersion(4, 8, 10),
        PypeVersion(4, 8, 20),
        PypeVersion(4, 8, 9),
        PypeVersion(1, 2, 3, variant="staging"),
        PypeVersion(1, 2, 3, client="client")
    ]
    res = sorted(sort_versions)

    assert res[0] == sort_versions[2]
    assert res[1] == sort_versions[6]
    assert res[2] == sort_versions[1]
    assert res[-1] == sort_versions[4]

    str_versions = [
        "5.5.1",
        "5.5.2-client",
        "5.5.3-client-strange",
        "5.5.4-staging",
        "5.5.5-staging-client",
        "5.6.3",
        "5.6.3-staging"
    ]
    res_versions = []
    for v in str_versions:
        res_versions.append(PypeVersion(version=v))

    sorted_res_versions = sorted(res_versions)

    assert str(sorted_res_versions[0]) == str_versions[0]
    assert str(sorted_res_versions[-1]) == str_versions[5]

    with pytest.raises(ValueError):
        _ = PypeVersion()

    with pytest.raises(ValueError):
        _ = PypeVersion(major=1)

    with pytest.raises(ValueError):
        _ = PypeVersion(version="booobaa")

    v11 = PypeVersion(version="4.6.7-client-staging")
    assert v11.major == 4
    assert v11.minor == 6
    assert v11.subversion == 7
    assert v11.variant == "staging"
    assert v11.client == "client"


def test_get_main_version():
    ver = PypeVersion(1, 2, 3, variant="staging", client="foo")
    assert ver.get_main_version() == "1.2.3"


def test_get_version_path_from_list():
    versions = [
        PypeVersion(1, 2, 3, path=Path('/foo/bar')),
        PypeVersion(3, 4, 5, variant="staging", path=Path("/bar/baz")),
        PypeVersion(6, 7, 8, client="x", path=Path("boo/goo"))
    ]
    path = BootstrapRepos.get_version_path_from_list(
        "3.4.5-staging", versions)

    assert path == Path("/bar/baz")


def test_search_string_for_pype_version(printer):
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
        assert PypeVersion.version_in_str(ver_string[0])[0] == ver_string[1]


def test_install_live_repos(fix_bootstrap, printer):
    rf = fix_bootstrap.create_version_from_live_code()
    sep = os.path.sep
    expected_paths = [
        f"{rf}{sep}avalon-core",
        f"{rf}{sep}avalon-unreal-integration",
        f"{rf}{sep}maya-look-assigner",
        f"{rf}{sep}pype"
    ]
    printer("testing zip creation")
    assert os.path.exists(rf), "zip archive was not created"
    fix_bootstrap.add_paths_from_archive(rf)
    for ep in expected_paths:
        assert ep in sys.path, f"{ep} not set correctly"

    printer("testing pype imported")
    del sys.modules["pype"]
    import pype  # noqa: F401

    # test if pype is imported from specific location in zip
    print(pype.__file__)
    assert "pype" in sys.modules.keys(), "Pype not imported"
    assert sys.modules["pype"].__file__ == \
        f"{rf}{sep}pype{sep}pype{sep}__init__.py"


def test_find_pype(fix_bootstrap, tmp_path_factory, monkeypatch, printer):

    test_pype = namedtuple("Pype", "prefix version suffix type valid")

    test_versions_1 = [
        test_pype(prefix="foo-v", version="5.5.1",
                  suffix=".zip", type="zip", valid=False),
        test_pype(prefix="bar-v", version="5.5.2-client",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="baz-v", version="5.5.3-client-strange",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="bum-v", version="5.5.4-staging",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="zum-v", version="5.5.5-client-staging",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="fam-v", version="5.6.3",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="foo-v", version="5.6.3-staging",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="fim-v", version="5.6.3",
                  suffix=".zip", type="zip", valid=False),
        test_pype(prefix="foo-v", version="5.6.4",
                  suffix=".txt", type="txt", valid=False),
        test_pype(prefix="foo-v", version="5.7.1",
                  suffix="", type="dir", valid=False),
    ]

    test_versions_2 = [
        test_pype(prefix="foo-v", version="10.0.0",
                  suffix=".txt", type="txt", valid=False),
        test_pype(prefix="lom-v", version="7.2.6",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="bom-v", version="7.2.7-client",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="woo-v", version="7.2.8-client-strange",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="loo-v", version="7.2.10-client-staging",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="kok-v", version="7.0.1",
                  suffix=".zip", type="zip", valid=True)
    ]

    test_versions_3 = [
        test_pype(prefix="foo-v", version="3.0.0",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="goo-v", version="3.0.1",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="hoo-v", version="4.1.0",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="foo-v", version="4.1.2",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="foo-v", version="3.0.1-client",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="foo-v", version="3.0.1-client-strange",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="foo-v", version="3.0.1-staging",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="foo-v", version="3.0.1-client-staging",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="foo-v", version="3.2.0",
                  suffix=".zip", type="zip", valid=True)
    ]

    test_versions_4 = [
        test_pype(prefix="foo-v", version="10.0.0",
                  suffix="", type="dir", valid=True),
        test_pype(prefix="lom-v", version="11.2.6",
                  suffix=".zip", type="dir", valid=False),
        test_pype(prefix="bom-v", version="7.2.7-client",
                  suffix=".zip", type="zip", valid=True),
        test_pype(prefix="woo-v", version="7.2.8-client-strange",
                  suffix=".zip", type="txt", valid=False)
    ]

    def _create_invalid_zip(path: Path):
        with ZipFile(path, "w") as zf:
            zf.writestr("test.foo", "test")

    def _create_valid_zip(path: Path, version: str):
        with ZipFile(path, "w") as zf:
            zf.writestr(
                "pype/pype/version.py", f"__version__ = '{version}'\n\n")

    def _create_invalid_dir(path: Path):
        path.mkdir(parents=True, exist_ok=True)
        with open(path / "invalid", "w") as fp:
            fp.write("invalid")

    def _create_valid_dir(path: Path, version: str):
        pype_path = path / "pype" / "pype"
        version_path = pype_path / "version.py"
        pype_path.mkdir(parents=True, exist_ok=True)
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

    # in PYPE_PATH
    e_path = tmp_path_factory.mktemp("environ")

    # create files and directories for test
    for test_file in test_versions_1:
        _build_test_item(e_path, test_file)

    # in pypePath registry
    p_path = tmp_path_factory.mktemp("pypePath")
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

    printer("testing finding Pype in given path ...")
    result = fix_bootstrap.find_pype(g_path, include_zips=True)
    # we should have results as file were created
    assert result is not None, "no Pype version found"
    # latest item in `result` should be latest version found.
    expected_path = Path(
        g_path / "{}{}{}".format(
            test_versions_3[3].prefix,
            test_versions_3[3].version,
            test_versions_3[3].suffix
        )
    )
    assert result, "nothing found"
    assert result[-1].path == expected_path, "not a latest version of Pype 3"

    monkeypatch.setenv("PYPE_PATH", e_path.as_posix())

    result = fix_bootstrap.find_pype(include_zips=True)
    # we should have results as file were created
    assert result is not None, "no Pype version found"
    # latest item in `result` should be latest version found.
    expected_path = Path(
        e_path / "{}{}{}".format(
            test_versions_1[5].prefix,
            test_versions_1[5].version,
            test_versions_1[5].suffix
        )
    )
    assert result, "nothing found"
    assert result[-1].path == expected_path, "not a latest version of Pype 1"

    monkeypatch.delenv("PYPE_PATH", raising=False)

    # mock appdirs user_data_dir
    def mock_user_data_dir(*args, **kwargs):
        return d_path.as_posix()

    monkeypatch.setattr(appdirs, "user_data_dir", mock_user_data_dir)
    fix_bootstrap.registry = PypeSettingsRegistry()
    fix_bootstrap.registry.set_item("pypePath", d_path.as_posix())

    result = fix_bootstrap.find_pype(include_zips=True)
    # we should have results as file were created
    assert result is not None, "no Pype version found"
    # latest item in `result` should be latest version found.
    expected_path = Path(
        d_path / "{}{}{}".format(
            test_versions_2[3].prefix,
            test_versions_2[3].version,
            test_versions_2[3].suffix
        )
    )
    assert result, "nothing found"
    assert result[-1].path == expected_path, "not a latest version of Pype 2"

    result = fix_bootstrap.find_pype(e_path, include_zips=True)
    assert result is not None, "no Pype version found"
    expected_path = Path(
        e_path / "{}{}{}".format(
            test_versions_1[5].prefix,
            test_versions_1[5].version,
            test_versions_1[5].suffix
        )
    )
    assert result[-1].path == expected_path, "not a latest version of Pype 1"

    result = fix_bootstrap.find_pype(dir_path, include_zips=True)
    assert result is not None, "no Pype versions found"
    expected_path = Path(
        dir_path / "{}{}{}".format(
            test_versions_4[0].prefix,
            test_versions_4[0].version,
            test_versions_4[0].suffix
        )
    )
    assert result[-1].path == expected_path, "not a latest version of Pype 4"
