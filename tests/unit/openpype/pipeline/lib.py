import pytest
from tests.lib.testing_classes import ModuleUnitTest
from openpype.pipeline import legacy_io


class TestPipeline(ModuleUnitTest):
    """ Testing Pipeline base class
    """

    @pytest.fixture(scope="module")
    def legacy_io(self, dbcon):
        legacy_io.Session = dbcon.Session
        yield legacy_io.Session
