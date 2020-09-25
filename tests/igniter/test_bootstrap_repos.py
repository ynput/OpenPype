# -*- coding: utf-8 -*-
"""Test suite for repos bootstrapping (install)."""
import os
import sys
import pytest
from igniter.bootstrap_repos import BootstrapRepos


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


def test_find_pype(fix_bootstrap):
    test_versions = [
        "pype-repositories-v3.0.0.zip",
        "pype-repositories-v3.0.1.zip",
        "pype-repositories-v4.1.0.zip",
        "pype-repositories-v4.1.2.zip",
        "pype-repositories-v3.2.0.zip",
    ]
    for test_file in test_versions:
        with open(os.path.join(fix_bootstrap.data_dir, test_file), "w") as fp:
            fp.write(test_file)

    result = fix_bootstrap.find_pype()
    # we should have results as file were created
    assert result is not None, "no Pype version found"
    # latest item in `result` should be latest version found.
    assert list(result.values())[-1] == os.path.join(
        fix_bootstrap.data_dir, test_versions[3]), "not a latest version of Pype"
