# -*- coding: utf-8 -*-
import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--test_data_folder", action="store", default=None,
        help="Provide url of a folder of unzipped test file"
    )

@pytest.fixture(scope="module")
def test_data_folder(request):
    return request.config.getoption("--test_data_folder")