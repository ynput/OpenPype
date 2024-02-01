# -*- coding: utf-8 -*-
# adds command line arguments for 'runtests' as a fixtures
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--test_data_folder", action="store", default=None,
        help="Provide url of a folder of unzipped test file"
    )

    parser.addoption(
        "--persist", action="store", default=None,
        help="True - keep test_db, test_openpype, outputted test files"
    )

    parser.addoption(
        "--app_group", action="store", default=None,
        help="Keep empty to use default application or explicit"
    )

    parser.addoption(
        "--app_variant", action="store", default=None,
        help="Keep empty to locate latest installed variant or explicit"
    )

    parser.addoption(
        "--timeout", action="store", default=None,
        help="Overwrite default timeout"
    )

    parser.addoption(
        "--setup_only", action="store", default=None,
        help="True - only setup test, do not run any tests"
    )

    parser.addoption(
        "--mongo_url", action="store", default=None,
        help="Provide url of the Mongo database."
    )

    parser.addoption(
        "--dump_databases", action="store", default=None,
        help="Dump databases to data folder."
    )


@pytest.fixture(scope="module")
def test_data_folder(request):
    return request.config.getoption("--test_data_folder")


@pytest.fixture(scope="module")
def persist(request):
    return request.config.getoption("--persist")


@pytest.fixture(scope="module")
def app_group(request):
    return request.config.getoption("--app_group")


@pytest.fixture(scope="module")
def app_variant(request):
    return request.config.getoption("--app_variant")


@pytest.fixture(scope="module")
def timeout(request):
    return request.config.getoption("--timeout")


@pytest.fixture(scope="module")
def setup_only(request):
    return request.config.getoption("--setup_only")


@pytest.fixture(scope="module")
def mongo_url(request):
    return request.config.getoption("--mongo_url")


@pytest.fixture(scope="module")
def dump_databases(request):
    return request.config.getoption("--dump_databases")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # set a report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"

    setattr(item, "rep_" + rep.when, rep)

    # In the event of module scoped fixtures, also mark failure in module.
    module = item
    while module is not None and not isinstance(module, pytest.Module):
        module = module.parent
    if module is not None:
        if rep.when == 'call' and (rep.failed or rep.skipped):
            module.module_test_failure = True
