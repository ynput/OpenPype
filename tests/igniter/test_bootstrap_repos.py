# -*- coding: utf-8 -*-
"""Test suite for repos bootstrapping (install)."""
import os
import sys
import pytest
from igniter.bootstrap_repos import BootstrapRepos


@pytest.fixture
def fix_bootrap(tmp_path_factory):
    bs = BootstrapRepos()
    bs.live_repo_dir = os.path.abspath('repos')
    session_temp = tmp_path_factory.mktemp('test_bootstrap')
    bs.data_dir = session_temp
    return bs


def test_install_live_repos(fix_bootrap, printer):
    rf = fix_bootrap.install_live_repos()
    expected_paths = [
        f"{rf}{os.path.sep}acre",
        f"{rf}{os.path.sep}avalon-core",
        f"{rf}{os.path.sep}avalon-unreal-integration",
        f"{rf}{os.path.sep}maya-look-assigner",
        f"{rf}{os.path.sep}pyblish-base",
        f"{rf}{os.path.sep}pype",
        f"{rf}{os.path.sep}pype-config"
    ]
    assert os.path.exists(rf), "zip archive was not created"
    fix_bootrap.add_paths_from_archive(rf)
    for ep in expected_paths:
        assert ep in sys.path, f"{ep} not set correctly"

    import pype
