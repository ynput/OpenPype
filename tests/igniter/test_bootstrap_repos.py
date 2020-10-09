# -*- coding: utf-8 -*-
"""Test suite for repos bootstrapping (install)."""
import os
import sys
from pathlib import Path
import pytest
import appdirs
from igniter.bootstrap_repos import BootstrapRepos
from pype.lib import PypeSettingsRegistry


@pytest.fixture
def fix_bootstrap(tmp_path):
    bs = BootstrapRepos()
    bs.live_repo_dir = os.path.abspath('repos')
    bs.data_dir = tmp_path
    return bs


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
        "pype-repositories-v5.6.3.zip",
    ]

    test_versions_2 = [
        "pype-repositories-v7.2.6.zip",
        "pype-repositories-v7.0.1.zip",
    ]

    test_versions_3 = [
        "pype-repositories-v3.0.0.zip",
        "pype-repositories-v3.0.1.zip",
        "pype-repositories-v4.1.0.zip",
        "pype-repositories-v4.1.2.zip",
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
    assert list(result.values())[-1] == Path(
        fix_bootstrap.data_dir / test_versions_3[3]
    ), "not a latest version of Pype 3"

    monkeypatch.setenv("PYPE_PATH", e_path.as_posix())

    result = fix_bootstrap.find_pype()
    # we should have results as file were created
    assert result is not None, "no Pype version found"
    # latest item in `result` should be latest version found.
    assert list(result.values())[-1] == Path(
        e_path / test_versions_1[1]
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
    assert list(result.values())[-1] == Path(
        r_path / test_versions_2[0]
    ), "not a latest version of Pype 2"
