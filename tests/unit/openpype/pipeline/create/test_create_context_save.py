import pyblish.api

from openpype.pipeline import registered_host

from openpype.lib import BoolDef

from openpype.pipeline.publish import OpenPypePyblishPluginMixin
from openpype.pipeline.create import (
    register_creator_plugin,
    deregister_creator_plugin,
    CreateContext,
)

import pytest
from tests.unit.openpype.pipeline.create.lib import test_setup, DummyCreator
from tests.lib.testing_classes import ModuleUnitTest


class TestCreateContext(ModuleUnitTest):
    """ Testing Colorspace

    Example:
        cd to OpenPype repo root dir
        poetry run python ./start.py runtests <openpype_root>/tests/unit/openpype/pipeline/test_create_context_save.py
    """  # noqa: E501

    @pytest.fixture
    def setup_dummy_host(self):
        """Register DummyHost without ANY plugins"""
        with test_setup():
            yield

    @pytest.fixture
    def dummy_creator(self):
        """Register DummyCreator"""
        register_creator_plugin(DummyCreator)
        yield DummyCreator
        deregister_creator_plugin(DummyCreator)

    def test_save_instance_publish_attribute_changes(self,
                                                     setup_dummy_host,
                                                     dummy_creator):
        """Test CreateContext instance publish attribute change saves.

        Test whether changes on CreatedInstance publish attributes are marked
        as stored when `CreateContext.save_changes()` is triggered and that
        no full `CreateContext.reset()` is required to update values and
        that the changes actually go through `Creator.update_instances` to
        persist the changes made as intended.

        """

        # Def
        class Plugin(pyblish.api.InstancePlugin,
                     OpenPypePyblishPluginMixin):
            """Publish Plug-in that exposes bool attribute definition"""
            order = pyblish.api.ValidatorOrder

            @classmethod
            def get_attribute_defs(cls):
                return [
                    BoolDef("state",
                            label="State",
                            default=False)
                ]

        pyblish.api.register_plugin(Plugin)

        create_context = CreateContext(host=registered_host())
        create_context.create(
            creator_identifier=dummy_creator.identifier,
            variant="main"
        )
        # Save the initial state of the attribute defs
        create_context.save_changes()

        instances = list(create_context.instances)
        assert len(instances) == 1, "Must have one instance"
        instance = instances[0]

        def get_saved_state_in_host():
            """Return 'host stored' state value for instance"""
            return (
                dummy_creator.cache["instances"][instance.id]
                ["publish_attributes"]["Plugin"]["state"]
            )

        # Value must be unchanged and False
        assert instance.publish_attributes["Plugin"]["state"] is False
        assert get_saved_state_in_host() is False  # noqa
        assert instance.changes().changed is False

        # Set to True, value must be changed before save, and unchanged after
        # and host value must be updated along
        instance.publish_attributes["Plugin"]["state"] = True
        assert instance.changes().changed is True
        create_context.save_changes()
        assert instance.changes().changed is False
        assert instance.publish_attributes["Plugin"]["state"] is True
        assert get_saved_state_in_host() is True

        # Set to False, value must be changed before save, and unchanged after
        # and host value must be updated along
        instance.publish_attributes["Plugin"]["state"] = False
        assert instance.changes().changed is True
        create_context.save_changes()
        assert instance.changes().changed is False
        assert instance.publish_attributes["Plugin"]["state"] is False
        assert get_saved_state_in_host() is False

        pyblish.api.deregister_plugin(Plugin)

    def test_create_and_remove_instances(self,
                                         setup_dummy_host,
                                         dummy_creator):
        """Test creation, removal and persistence of instances on resets"""

        create_context = CreateContext(host=registered_host())
        create_context.create(
            creator_identifier=dummy_creator.identifier,
            variant="A"
        )
        create_context.create(
            creator_identifier=dummy_creator.identifier,
            variant="B"
        )
        create_context.create(
            creator_identifier=dummy_creator.identifier,
            variant="C"
        )

        # There should be three instances
        instances = list(create_context.instances)
        assert len(instances) == 3

        # Remove one instance
        create_context.remove_instances([instances[-1]])
        assert len(instances) == 2

        # Make sure instances persist a reset
        create_context.reset()
        instances = list(create_context.instances)
        assert len(instances) == 2

        # Make sure instances are also found from a new Create Context
        create_context = CreateContext(host=registered_host())
        instances = list(create_context.instances)
        assert len(instances) == 2
