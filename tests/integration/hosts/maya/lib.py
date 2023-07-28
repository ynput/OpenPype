from tests.lib.testing_classes import (
    HostFixtures,
    PublishTest,
    DeadlinePublishTest
)


class MayaLocalPublishTestClass(HostFixtures, PublishTest):
    """Testing class for local publishes."""


class MayaDeadlinePublishTestClass(HostFixtures, DeadlinePublishTest):
    """Testing class for Deadline publishes."""
