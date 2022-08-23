import os
from openpype.settings import get_local_settings

# Constant key under which local settings are stored
LOCAL_EXPERIMENTAL_KEY = "experimental_tools"


class ExperimentalTool(object):
    """Definition of experimental tool.

    Definition is used in local settings.

    Args:
        identifier (str): String identifier of tool (unique).
        label (str): Label shown in UI.
    """
    def __init__(self, identifier, label, tooltip):
        self.identifier = identifier
        self.label = label
        self.tooltip = tooltip
        self._enabled = True

    @property
    def enabled(self):
        """Is tool enabled and button is clickable."""
        return self._enabled

    def set_enabled(self, enabled=True):
        """Change if tool is enabled."""
        self._enabled = enabled


class ExperimentalHostTool(ExperimentalTool):
    """Definition of experimental tool.

    Definition is used in local settings and in experimental tools dialog.

    Args:
        identifier (str): String identifier of tool (unique).
        label (str): Label shown in UI.
        callback (function): Callback for UI button.
        tooltip (str): Tooltip showed on button.
        hosts_filter (list): List of host names for which is tool available.
            Some tools may not be available in all hosts.
    """
    def __init__(
        self, identifier, label, tooltip, callback, hosts_filter=None
    ):
        super(ExperimentalHostTool, self).__init__(identifier, label, tooltip)
        self.callback = callback
        self.hosts_filter = hosts_filter
        self._enabled = True

    def is_available_for_host(self, host_name):
        if self.hosts_filter:
            return host_name in self.hosts_filter
        return True

    def execute(self, *args, **kwargs):
        """Trigger registered callback."""
        self.callback(*args, **kwargs)


class ExperimentalTools:
    """Wrapper around experimental tools.

    To add/remove experimental tool just add/remove tool to
    `experimental_tools` variable in __init__ function.

    --- Example tool (callback will just print on click) ---
    def example_callback(*args):
        print("Triggered tool")

    experimental_tools = [
        ExperimentalHostTool(
            "example",
            "Example experimental tool",
            example_callback,
            "Example tool tooltip."
        )
    ]
    ---
    """
    def __init__(self, parent_widget=None, refresh=True):
        # Definition of experimental tools
        experimental_tools = [
            ExperimentalHostTool(
                "publisher",
                "New publisher",
                "Combined creation and publishing into one tool.",
                self._show_publisher
            ),
            ExperimentalTool(
                "traypublisher",
                "New Standalone Publisher",
                "Standalone publisher using new publisher. Requires restart"
            )
        ]

        # Store tools by identifier
        tools_by_identifier = {}
        for tool in experimental_tools:
            if tool.identifier in tools_by_identifier:
                raise KeyError((
                    "Duplicated experimental tool identifier \"{}\""
                ).format(tool.identifier))
            tools_by_identifier[tool.identifier] = tool

        self._tools_by_identifier = tools_by_identifier
        self._tools = experimental_tools

        self._parent_widget = parent_widget
        self._publisher_tool = None

        if refresh:
            self.refresh_availability()

    @property
    def tools(self):
        """Tools in list.

        Returns:
            list: Tools filtered by host name if filtering was enabled
                on initialization.
        """
        return self._tools

    @property
    def tools_by_identifier(self):
        """Tools by their identifier.

        Returns:
            dict: Tools by identifier filtered by host name if filtering
                was enabled on initialization.
        """
        return self._tools_by_identifier

    def get(self, tool_identifier):
        """Get tool by identifier."""
        return self.tools_by_identifier.get(tool_identifier)

    def get_tools_for_host(self, host_name=None):
        if not host_name:
            host_name = os.environ.get("AVALON_APP")
        tools = []
        for tool in self.tools:
            if (
                isinstance(tool, ExperimentalHostTool)
                and tool.is_available_for_host(host_name)
            ):
                tools.append(tool)
        return tools

    def refresh_availability(self):
        """Reload local settings and check if any tool changed ability."""
        local_settings = get_local_settings()
        experimental_settings = (
            local_settings.get(LOCAL_EXPERIMENTAL_KEY)
        ) or {}

        for identifier, eperimental_tool in self.tools_by_identifier.items():
            enabled = experimental_settings.get(identifier, False)
            eperimental_tool.set_enabled(enabled)

    def _show_publisher(self):
        if self._publisher_tool is None:
            from openpype.tools import publisher

            self._publisher_tool = publisher.PublisherWindow(
                parent=self._parent_widget
            )

        self._publisher_tool.show()
