# -*- coding: utf-8 -*-
"""Test suite for repos bootstrapping (install)."""
import os
import sys
from pathlib import Path
import pytest
import appdirs
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

    v3 = PypeVersion(1, 2, 3, variant="staging")
    assert str(v3) == "1.2.3-staging"

    v4 = PypeVersion(1, 2, 3, variant="staging", client="client")
    assert str(v4) == "1.2.3-staging-client"

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

    v11 = PypeVersion(version="4.6.7-staging-client")
    assert v11.major == 4
    assert v11.minor == 6
    assert v11.subversion == 7
    assert v11.variant == "staging"
    assert v11.client == "client"


def test_get_version_path_from_list():
    versions = [
        PypeVersion(1, 2, 3, path=Path('/foo/bar')),
        PypeVersion(3, 4, 5, variant="staging", path=Path("/bar/baz")),
        PypeVersion(6, 7, 8, client="x", path=Path("boo/goo"))
    ]
    path = BootstrapRepos.get_version_path_from_list(
        "3.4.5-staging", versions)

    assert path == Path("/bar/baz")


def test_install_live_repos(fix_bootstrap, printer):
    rf = fix_bootstrap.install_live_repos()
    sep = os.path.sep
    expected_paths = [
        f"{rf}{sep}acre",
        f"{rf}{sep}avalon-core",
        f"{rf}{sep}avalon-unreal-integration",
        f"{rf}{sep}maya-look-assigner",
        f"{rf}{sep}pyblish-base",
        f"{rf}{sep}pype",
        f"{rf}{sep}pype-config"
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

    test_versions_1 = [
        "pype-repositories-v5.5.1.zip",
        "pype-repositories-v5.5.2-client.zip",
        "pype-repositories-v5.5.3-client-strange.zip",
        "pype-repositories-v5.5.4-staging.zip",
        "pype-repositories-v5.5.5-staging-client.zip",
        "pype-repositories-v5.6.3.zip",
        "pype-repositories-v5.6.3-staging.zip"
    ]

    test_versions_2 = [
        "pype-repositories-v7.2.6.zip",
        "pype-repositories-v7.2.7-client.zip",
        "pype-repositories-v7.2.8-client-strange.zip",
        "pype-repositories-v7.2.9-staging.zip",
        "pype-repositories-v7.2.10-staging-client.zip",
        "pype-repositories-v7.0.1.zip",
    ]

    test_versions_3 = [
        "pype-repositories-v3.0.0.zip",
        "pype-repositories-v3.0.1.zip",
        "pype-repositories-v4.1.0.zip",
        "pype-repositories-v4.1.2.zip",
        "pype-repositories-v3.0.1-client.zip",
        "pype-repositories-v3.0.1-client-strange.zip",
        "pype-repositories-v3.0.1-staging.zip",
        "pype-repositories-v3.0.1-staging-client.zip",
        "pype-repositories-v3.2.0.zip",
    ]

    # in PYPE_PATH
    e_path = tmp_path_factory.mktemp("environ")
    for test_file in test_versions_1:
        with open(e_path / test_file, "w") as fp:
            fp.write(test_file)

    # in pypePath registry
    r_path = tmp_path_factory.mktemp("pypePath")
    for test_file in test_versions_2:
        with open(r_path / test_file, "w") as fp:
            fp.write(test_file)

    # in data dir
    for test_file in test_versions_3:
        with open(os.path.join(fix_bootstrap.data_dir, test_file), "w") as fp:
            fp.write(test_file)

    result = fix_bootstrap.find_pype()
    # we should have results as file were created
    assert result is not None, "no Pype version found"
    # latest item in `result` should be latest version found.
    assert result[-1].path == Path(
        fix_bootstrap.data_dir / test_versions_3[3]
    ), "not a latest version of Pype 3"

    monkeypatch.setenv("PYPE_PATH", e_path.as_posix())

    result = fix_bootstrap.find_pype()
    # we should have results as file were created
    assert result is not None, "no Pype version found"
    # latest item in `result` should be latest version found.
    assert result[-1].path == Path(
        e_path / test_versions_1[5]
    ), "not a latest version of Pype 1"

    monkeypatch.delenv("PYPE_PATH", raising=False)

    # mock appdirs user_data_dir
    def mock_user_data_dir(*args, **kwargs):
        return r_path.as_posix()

    monkeypatch.setattr(appdirs, "user_data_dir", mock_user_data_dir)
    fix_bootstrap.registry = PypeSettingsRegistry()
    fix_bootstrap.registry.set_item("pypePath", r_path.as_posix())

    result = fix_bootstrap.find_pype()
    # we should have results as file were created
    assert result is not None, "no Pype version found"
    # latest item in `result` should be latest version found.
    assert result[-1].path == Path(
        r_path / test_versions_2[4]
    ), "not a latest version of Pype 2"

    result = fix_bootstrap.find_pype(e_path)
    assert result is not None, "no Pype version found"
    assert result[-1].path == Path(
        e_path / test_versions_1[5]
    ), "not a latest version of Pype 1"
