import os

from tests.lib.testing_classes import (
    HostFixtures,
    PublishTest,
    DeadlinePublishTest
)


LOG_PATH = os.path.join("output.log")


class MayaLocalPublishTestClass(HostFixtures, PublishTest):
    """Testing class for local publishes."""


class MayaDeadlinePublishTestClass(HostFixtures, DeadlinePublishTest):
    """Testing class for Deadline publishes."""
