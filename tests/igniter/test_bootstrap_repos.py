# -*- coding: utf-8 -*-
"""Test suite for repos bootstrapping (install)."""
import os
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
    printer(f"repo: {fix_bootrap.live_repo_dir}")
    printer(f"data: {fix_bootrap.data_dir}")
    rf = fix_bootrap.install_live_repos()
    assert os.path.exists(rf), "zip archive was not created"
