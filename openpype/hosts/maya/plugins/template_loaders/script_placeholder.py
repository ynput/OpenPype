from maya import cmds

from openpype.hosts.maya.api.workfile_template_builder import (
    MayaPlaceholderPlugin
)
from openpype.lib import NumberDef, TextDef, EnumDef
from openpype.lib.events import weakref_partial


EXAMPLE_SCRIPT = """
# Access maya commands
from maya import cmds

# Access the placeholder node
placeholder_node = placeholder.scene_identifier

# Access the event callback
if event is None:
    print(f"Populating {placeholder}")
else:
    if event.topic == "template.depth_processed":
        print(f"Processed depth: {event.get('depth')}")
    elif event.topic == "template.finished":
        print("Build finished.")
""".strip()


class MayaPlaceholderScriptPlugin(MayaPlaceholderPlugin):
    """Execute a script at the given `order` during workfile build.

    This is a very low-level placeholder to run Python scripts at a given
    point in time during the workfile template build.

    It can create either a locator or an objectSet as placeholder node.
    It defaults to an objectSet, since allowing to run on e.g. other
    placeholder node members can be useful, e.g. using:

    >>> members = cmds.sets(placeholder.scene_identifier, query=True)

    """

    identifier = "maya.runscript"
    label = "Run Python Script"

    use_selection_as_parent = False

    def get_placeholder_options(self, options=None):
        options = options or {}
        return [
            NumberDef(
                "order",
                label="Order",
                default=options.get("order") or 0,
                decimals=0,
                minimum=0,
                maximum=999,
                tooltip=(
                    "Order"
                    "\nOrder defines asset loading priority (0 to 999)"
                    "\nPriority rule is : \"lowest is first to load\"."
                )
            ),
            TextDef(
                "prepare_script",
                label="Run at\nprepare",
                tooltip="Run before populate at prepare order",
                multiline=True,
                default=options.get("prepare_script", "")
            ),
            TextDef(
                "populate_script",
                label="Run at\npopulate",
                tooltip="Run script at populate node order<br>"
                        "This is the <b>default</b> behavior",
                multiline=True,
                default=options.get("populate_script", EXAMPLE_SCRIPT)
            ),
            TextDef(
                "depth_processed_script",
                label="Run after\ndepth\niteration",
                tooltip="Run script after every build depth iteration",
                multiline=True,
                default=options.get("depth_processed_script", "")
            ),
            TextDef(
                "finished_script",
                label="Run after\nbuild",
                tooltip=(
                    "Run script at build finished.<br>"
                    "<b>Note</b>: this even runs if other placeholders had "
                    "errors during the build"
                ),
                multiline=True,
                default=options.get("finished_script", "")
            ),
            EnumDef(
                "create_nodetype",
                label="Nodetype",
                items={
                    "spaceLocator": "Locator",
                    "objectSet": "ObjectSet"
                },
                tooltip=(
                    "The placeholder's node type to be created.<br>"
                    "<b>Note</b> this only works on create, not on update"
                ),
                default=options.get("create_nodetype", "objectSet")
            ),
        ]

    def create_placeholder(self, placeholder_data):
        nodetype = placeholder_data.get("create_nodetype", "objectSet")

        if nodetype == "spaceLocator":
            super(MayaPlaceholderScriptPlugin, self).create_placeholder(
                placeholder_data
            )
        elif nodetype == "objectSet":
            placeholder_data["plugin_identifier"] = self.identifier

            # Create maya objectSet on selection
            selection = cmds.ls(selection=True, long=True)
            name = self._create_placeholder_name(placeholder_data)
            node = cmds.sets(selection, name=name)

            self.imprint(node, placeholder_data)

    def prepare_placeholders(self, placeholders):
        super(MayaPlaceholderScriptPlugin, self).prepare_placeholders(
            placeholders
        )
        for placeholder in placeholders:
            prepare_script = placeholder.data.get("prepare_script")
            if not prepare_script:
                continue

            self.run_script(placeholder, prepare_script)

    def populate_placeholder(self, placeholder):

        populate_script = placeholder.data.get("populate_script")
        depth_script = placeholder.data.get("depth_processed_script")
        finished_script = placeholder.data.get("finished_script")

        # Run now
        if populate_script:
            self.run_script(placeholder, populate_script)

        if not any([depth_script, finished_script]):
            # No callback scripts to run
            if not placeholder.data.get("keep_placeholder", True):
                self.delete_placeholder(placeholder)
            return

        # Run at each depth processed
        if depth_script:
            callback = weakref_partial(self.run_script,
                                       placeholder,
                                       depth_script)
            self.register_on_depth_processed_callback(placeholder,
                                                      callback,
                                                      order=placeholder.order)

        # Run at build finish
        if finished_script:
            callback = weakref_partial(self.run_script,
                                       placeholder,
                                       finished_script)
            self.register_on_finished_callback(placeholder,
                                               callback,
                                               order=placeholder.order)

        # If placeholder should be deleted, delete it after finish so
        # the scripts have access to it up to the last run
        if not placeholder.data.get("keep_placeholder", True):
            delete_callback = weakref_partial(
                self.delete_placeholder,
                placeholder
            )
            self.register_on_finished_callback(placeholder,
                                               delete_callback,
                                               order=placeholder.order + 1)

    def run_script(self, placeholder, script, event=None):
        """Run script

        Even though `placeholder` is an unused arguments by exposing it as
        an input argument it means it makes it available through
        globals()/locals() in the `exec` call, giving the script access
        to the placeholder.

        For example:
        >>> node = placeholder.scene_identifier

        In the case the script is running at a callback level (not during
        populate) then it has access to the `event` as well, otherwise the
        value is None if it runs during `populate_placeholder` directly.

        For example adding this as the callback script:
        >>> if event is not None:
        >>>     if event.topic == "on_depth_processed":
        >>>         print(f"Processed depth: {event.get('depth')}")
        >>>     elif event.topic == "on_finished":
        >>>         print("Build finished.")

        """
        self.log.debug(f"Running script at event: {event}")
        exec(script, locals())
