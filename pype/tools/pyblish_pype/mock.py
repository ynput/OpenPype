import os
import time
import subprocess

import pyblish.api


class MyAction(pyblish.api.Action):
    label = "My Action"
    on = "processed"

    def process(self, context, plugin):
        self.log.info("Running!")


class MyOtherAction(pyblish.api.Action):
    label = "My Other Action"

    def process(self, context, plugin):
        self.log.info("Running!")


class CollectComment(pyblish.api.ContextPlugin):
    """This collector has a very long comment.

    The idea is that this comment should either be elided, or word-
    wrapped in the corresponding view.

    """

    order = pyblish.api.CollectorOrder

    def process(self, context):
        context.data["comment"] = ""


class MyCollector(pyblish.api.ContextPlugin):
    label = "My Collector"
    order = pyblish.api.CollectorOrder

    def process(self, context):
        context.create_instance("MyInstance 1", families=["myFamily"])
        context.create_instance("MyInstance 2", families=["myFamily 2"])
        context.create_instance(
            "MyInstance 3",
            families=["myFamily 2"],
            publish=False
        )


class MyValidator(pyblish.api.InstancePlugin):
    order = pyblish.api.ValidatorOrder
    active = False
    label = "My Validator"
    actions = [MyAction,
               MyOtherAction]

    def process(self, instance):
        self.log.info("Validating: %s" % instance)


class MyExtractor(pyblish.api.InstancePlugin):
    order = pyblish.api.ExtractorOrder
    families = ["myFamily"]
    label = "My Extractor"

    def process(self, instance):
        self.log.info("Extracting: %s" % instance)


class CollectRenamed(pyblish.api.Collector):
    def process(self, context):
        i = context.create_instance("MyInstanceXYZ", family="MyFamily")
        i.set_data("name", "My instance")


class CollectNegatron(pyblish.api.Collector):
    """Negative collector adds Negatron"""

    order = pyblish.api.Collector.order - 0.49

    def process_context(self, context):
        self.log.info("Collecting Negatron")
        context.create_instance("Negatron", family="MyFamily")


class CollectPositron(pyblish.api.Collector):
    """Positive collector adds Positron"""

    order = pyblish.api.Collector.order + 0.49

    def process_context(self, context):
        self.log.info("Collecting Positron")
        context.create_instance("Positron", family="MyFamily")


class SelectInstances(pyblish.api.Selector):
    """Select debugging instances

    These instances are part of the evil plan to destroy the world.
    Be weary, be vigilant, be sexy.

    """

    def process_context(self, context):
        self.log.info("Selecting instances..")

        for instance in instances[:-1]:
            name, data = instance["name"], instance["data"]
            self.log.info("Selecting: %s" % name)
            instance = context.create_instance(name)

            for key, value in data.items():
                instance.set_data(key, value)


class SelectDiInstances(pyblish.api.Selector):
    """Select DI instances"""

    name = "Select Dependency Instances"

    def process(self, context):
        name, data = instances[-1]["name"], instances[-1]["data"]
        self.log.info("Selecting: %s" % name)
        instance = context.create_instance(name)

        for key, value in data.items():
            instance.set_data(key, value)


class SelectInstancesFailure(pyblish.api.Selector):
    """Select some instances, but fail before adding anything to the context.

    That's right. I'm programmed to fail. Try me.

    """

    __fail__ = True

    def process_context(self, context):
        self.log.warning("I'm about to fail")
        assert False, "I was programmed to fail"


class SelectInstances2(pyblish.api.Selector):
    def process(self, context):
        self.log.warning("I'm good")


class ValidateNamespace(pyblish.api.Validator):
    """Namespaces must be orange

    In case a namespace is not orange, report immediately to
    your officer in charge, ask for a refund, do a backflip.

    This has been an example of:

    - A long doc-string
    - With a list
    - And plenty of newlines and tabs.

    """

    families = ["B"]

    def process(self, instance):
        self.log.info("Validating the namespace of %s" % instance.data("name"))
        self.log.info("""And here's another message, quite long, in fact it's
too long to be displayed in a single row of text.
But that's how we roll down here. It's got \nnew lines\nas well.

- And lists
- And more lists

        """)


class ValidateContext(pyblish.api.Validator):
    families = ["A", "B"]

    def process_context(self, context):
        self.log.info("Processing context..")


class ValidateContextFailure(pyblish.api.Validator):
    optional = True
    families = ["C"]
    __fail__ = True

    def process_context(self, context):
        self.log.info("About to fail..")
        assert False, """I was programmed to fail

The reason I failed was because the sun was not aligned with the tides,
and the moon is gray; not yellow. Try again when the moon is yellow."""


class Validator1(pyblish.api.Validator):
    """Test of the order attribute"""
    order = pyblish.api.Validator.order + 0.1
    families = ["A"]

    def process_instance(self, instance):
        pass


class Validator2(pyblish.api.Validator):
    order = pyblish.api.Validator.order + 0.2
    families = ["B"]

    def process_instance(self, instance):
        pass


class Validator3(pyblish.api.Validator):
    order = pyblish.api.Validator.order + 0.3
    families = ["B"]

    def process_instance(self, instance):
        pass


class ValidateFailureMock(pyblish.api.Validator):
    """Plug-in that always fails"""
    optional = True
    order = pyblish.api.Validator.order + 0.1
    families = ["C"]
    __fail__ = True

    def process_instance(self, instance):
        self.log.debug("e = mc^2")
        self.log.info("About to fail..")
        self.log.warning("Failing.. soooon..")
        self.log.critical("Ok, you're done.")
        assert False, """ValidateFailureMock was destined to fail..

Here's some extended information about what went wrong.

It has quite the long string associated with it, including
a few newlines and a list.

- Item 1
- Item 2

"""


class ValidateIsIncompatible(pyblish.api.Validator):
    """This plug-in should never appear.."""
    requires = False  # This is invalid


class ValidateWithRepair(pyblish.api.Validator):
    """A validator with repair functionality"""
    optional = True
    families = ["C"]
    __fail__ = True

    def process_instance(self, instance):
        assert False, "%s is invalid, try repairing it!" % instance.name

    def repair_instance(self, instance):
        self.log.info("Attempting to repair..")
        self.log.info("Success!")


class ValidateWithRepairFailure(pyblish.api.Validator):
    """A validator with repair functionality that fails"""
    optional = True
    families = ["C"]
    __fail__ = True

    def process_instance(self, instance):
        assert False, "%s is invalid, try repairing it!" % instance.name

    def repair_instance(self, instance):
        self.log.info("Attempting to repair..")
        assert False, "Could not repair due to X"


class ValidateWithVeryVeryVeryLongLongNaaaaame(pyblish.api.Validator):
    """A validator with repair functionality that fails"""
    families = ["A"]


class ValidateWithRepairContext(pyblish.api.Validator):
    """A validator with repair functionality that fails"""
    optional = True
    families = ["C"]
    __fail__ = True

    def process_context(self, context):
        assert False, "Could not validate context, try repairing it"

    def repair_context(self, context):
        self.log.info("Attempting to repair..")
        assert False, "Could not repair"


class ExtractAsMa(pyblish.api.Extractor):
    """Extract contents of each instance into .ma

    Serialise scene using Maya's own facilities and then put
    it on the hard-disk. Once complete, this plug-in relies
    on a Conformer to put it in it's final location, as this
    extractor merely positions it in the users local temp-
    directory.

    """

    optional = True
    __expected__ = {
        "logCount": ">=4"
    }

    def process_instance(self, instance):
        self.log.info("About to extract scene to .ma..")
        self.log.info("Extraction went well, now verifying the data..")

        if instance.name == "Richard05":
            self.log.warning("You're almost running out of disk space!")

        self.log.info("About to finish up")
        self.log.info("Finished successfully")


class ConformAsset(pyblish.api.Conformer):
    """Conform the world

    Step 1: Conform all humans and Step 2: Conform all non-humans.
    Once conforming has completed, rinse and repeat.

    """

    optional = True

    def process_instance(self, instance):
        self.log.info("About to conform all humans..")

        if instance.name == "Richard05":
            self.log.warning("Richard05 is a conformist!")

        self.log.info("About to conform all non-humans..")
        self.log.info("Conformed Successfully")


class ValidateInstancesDI(pyblish.api.Validator):
    """Validate using the DI interface"""
    families = ["diFamily"]

    def process(self, instance):
        self.log.info("Validating %s.." % instance.data("name"))


class ValidateDIWithRepair(pyblish.api.Validator):
    families = ["diFamily"]
    optional = True
    __fail__ = True

    def process(self, instance):
        assert False, "I was programmed to fail, for repair"

    def repair(self, instance):
        self.log.info("Repairing %s" % instance.data("name"))


class ExtractInstancesDI(pyblish.api.Extractor):
    """Extract using the DI interface"""
    families = ["diFamily"]

    def process(self, instance):
        self.log.info("Extracting %s.." % instance.data("name"))


class ValidateWithLabel(pyblish.api.Validator):
    """Validate using the DI interface"""
    label = "Validate with Label"


class ValidateWithLongLabel(pyblish.api.Validator):
    """Validate using the DI interface"""
    label = "Validate with Loooooooooooooooooooooong Label"


class SimplePlugin1(pyblish.api.Plugin):
    """Validate using the simple-plugin interface"""

    def process(self):
        self.log.info("I'm a simple plug-in, only processed once")


class SimplePlugin2(pyblish.api.Plugin):
    """Validate using the simple-plugin interface

    It doesn't have an order, and will likely end up *before* all
    other plug-ins. (due to how sorted([1, 2, 3, None]) works)

    """

    def process(self, context):
        self.log.info("Processing the context, simply: %s" % context)


class SimplePlugin3(pyblish.api.Plugin):
    """Simply process every instance"""

    def process(self, instance):
        self.log.info("Processing the instance, simply: %s" % instance)


class ContextAction(pyblish.api.Action):
    label = "Context action"

    def process(self, context):
        self.log.info("I have access to the context")
        self.log.info("Context.instances: %s" % str(list(context)))


class FailingAction(pyblish.api.Action):
    label = "Failing action"

    def process(self):
        self.log.info("About to fail..")
        raise Exception("I failed")


class LongRunningAction(pyblish.api.Action):
    label = "Long-running action"

    def process(self):
        self.log.info("Sleeping for 2 seconds..")
        time.sleep(2)
        self.log.info("Ah, that's better")


class IconAction(pyblish.api.Action):
    label = "Icon action"
    icon = "crop"

    def process(self):
        self.log.info("I have an icon")


class PluginAction(pyblish.api.Action):
    label = "Plugin action"

    def process(self, plugin):
        self.log.info("I have access to my parent plug-in")
        self.log.info("Which is %s" % plugin.id)


class LaunchExplorerAction(pyblish.api.Action):
    label = "Open in Explorer"
    icon = "folder-open"

    def process(self, context):
        cwd = os.getcwd()
        self.log.info("Opening %s in Explorer" % cwd)
        result = subprocess.call("start .", cwd=cwd, shell=True)
        self.log.debug(result)


class ProcessedAction(pyblish.api.Action):
    label = "Success action"
    icon = "check"
    on = "processed"

    def process(self):
        self.log.info("I am only available on a successful plug-in")


class FailedAction(pyblish.api.Action):
    label = "Failure action"
    icon = "close"
    on = "failed"


class SucceededAction(pyblish.api.Action):
    label = "Success action"
    icon = "check"
    on = "succeeded"

    def process(self):
        self.log.info("I am only available on a successful plug-in")


class LongLabelAction(pyblish.api.Action):
    label = "An incredibly, incredicly looooon label. Very long."
    icon = "close"


class BadEventAction(pyblish.api.Action):
    label = "Bad event action"
    on = "not exist"


class InactiveAction(pyblish.api.Action):
    active = False


class PluginWithActions(pyblish.api.Validator):
    optional = True
    actions = [
        pyblish.api.Category("General"),
        ContextAction,
        FailingAction,
        LongRunningAction,
        IconAction,
        PluginAction,
        pyblish.api.Category("Empty"),
        pyblish.api.Category("OS"),
        LaunchExplorerAction,
        pyblish.api.Separator,
        FailedAction,
        SucceededAction,
        pyblish.api.Category("Debug"),
        BadEventAction,
        InactiveAction,
        LongLabelAction,
        pyblish.api.Category("Empty"),
    ]

    def process(self):
        self.log.info("Ran PluginWithActions")


class FailingPluginWithActions(pyblish.api.Validator):
    optional = True
    actions = [
        FailedAction,
        SucceededAction,
    ]

    def process(self):
        raise Exception("I was programmed to fail")


class ValidateDefaultOff(pyblish.api.Validator):
    families = ["A", "B"]
    active = False
    optional = True

    def process(self, instance):
        self.log.info("Processing instance..")


class ValidateWithHyperlinks(pyblish.api.Validator):
    """To learn about Pyblish

    <a href="http://pyblish.com">click here</a> (http://pyblish.com)

    """

    families = ["A", "B"]

    def process(self, instance):
        self.log.info("Processing instance..")

        msg = "To learn about Pyblish, <a href='http://pyblish.com'>"
        msg += "click here</a> (http://pyblish.com)"

        self.log.info(msg)


class LongRunningCollector(pyblish.api.Collector):
    """I will take at least 2 seconds..."""
    def process(self, context):
        self.log.info("Sleeping for 2 seconds..")
        time.sleep(2)
        self.log.info("Good morning")


class LongRunningValidator(pyblish.api.Validator):
    """I will take at least 2 seconds..."""
    def process(self, context):
        self.log.info("Sleeping for 2 seconds..")
        time.sleep(2)
        self.log.info("Good morning")


class RearrangingPlugin(pyblish.api.ContextPlugin):
    """Sort plug-ins by family, and then reverse it"""
    order = pyblish.api.CollectorOrder + 0.2

    def process(self, context):
        self.log.info("Reversing instances in the context..")
        context[:] = sorted(
            context,
            key=lambda i: i.data["family"],
            reverse=True
        )
        self.log.info("Reversed!")


class InactiveInstanceCollectorPlugin(pyblish.api.InstancePlugin):
    """Special case of an InstancePlugin running as a Collector"""
    order = pyblish.api.CollectorOrder + 0.1
    active = False

    def process(self, instance):
        raise TypeError("I shouldn't have run in the first place")


class CollectWithIcon(pyblish.api.ContextPlugin):
    order = pyblish.api.CollectorOrder

    def process(self, context):
        instance = context.create_instance("With Icon")
        instance.data["icon"] = "play"


instances = [
    {
        "name": "Peter01",
        "data": {
            "family": "A",
            "publish": False
        }
    },
    {
        "name": "Richard05",
        "data": {
            "family": "A",
        }
    },
    {
        "name": "Steven11",
        "data": {
            "family": "B",
        }
    },
    {
        "name": "Piraya12",
        "data": {
            "family": "B",
        }
    },
    {
        "name": "Marcus",
        "data": {
            "family": "C",
        }
    },
    {
        "name": "Extra1",
        "data": {
            "family": "C",
        }
    },
    {
        "name": "DependencyInstance",
        "data": {
            "family": "diFamily"
        }
    },
    {
        "name": "NoFamily",
        "data": {}
    },
    {
        "name": "Failure 1",
        "data": {
            "family": "failure",
            "fail": False
        }
    },
    {
        "name": "Failure 2",
        "data": {
            "family": "failure",
            "fail": True
        }
    }
]

plugins = [
    MyCollector,
    MyValidator,
    MyExtractor,

    CollectRenamed,
    CollectNegatron,
    CollectPositron,
    SelectInstances,
    SelectInstances2,
    SelectDiInstances,
    SelectInstancesFailure,
    ValidateFailureMock,
    ValidateNamespace,
    # ValidateIsIncompatible,
    ValidateWithVeryVeryVeryLongLongNaaaaame,
    ValidateContext,
    ValidateContextFailure,
    Validator1,
    Validator2,
    Validator3,
    ValidateWithRepair,
    ValidateWithRepairFailure,
    ValidateWithRepairContext,
    ValidateWithLabel,
    ValidateWithLongLabel,
    ValidateDefaultOff,
    ValidateWithHyperlinks,
    ExtractAsMa,
    ConformAsset,

    SimplePlugin1,
    SimplePlugin2,
    SimplePlugin3,

    ValidateInstancesDI,
    ExtractInstancesDI,
    ValidateDIWithRepair,

    PluginWithActions,
    FailingPluginWithActions,

    # LongRunningCollector,
    # LongRunningValidator,

    RearrangingPlugin,
    InactiveInstanceCollectorPlugin,

    CollectComment,
    CollectWithIcon,
]

pyblish.api.sort_plugins(plugins)
