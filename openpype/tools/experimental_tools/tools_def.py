import os
from openpype.settings import get_local_settings

# Constant key under which local settings are stored
LOCAL_EXPERIMENTAL_KEY = "experimental_tools"


class ExperimentalTool:
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
        self, identifier, label, callback, tooltip, hosts_filter=None
    ):
        self.identifier = identifier
        self.label = label
        self.callback = callback
        self.tooltip = tooltip
        self.hosts_filter = hosts_filter
        self._enabled = True

    def is_available_for_host(self, host_name):
        if self.hosts_filter:
            return host_name in self.hosts_filter
        return True

    @property
    def enabled(self):
        """Is tool enabled and button is clickable."""
        return self._enabled

    def set_enabled(self, enabled=True):
        """Change if tool is enabled."""
        self._enabled = enabled

    def execute(self):
        """Trigger registered callback."""
        self.callback()


class ExperimentalTools:
    """Wrapper around experimental tools.

    To add/remove experimental tool just add/remove tool to
    `experimental_tools` variable in __init__ function.

    Args:
        parent (QtWidgets.QWidget): Parent widget for tools.
        host_name (str): Name of host in which context we're now. Environment
            value 'AVALON_APP' is used when not passed.
        filter_hosts (bool): Should filter tools. By default is set to 'True'
            when 'host_name' is passed. Is always set to 'False' if 'host_name'
            is not defined.
    """
    def __init__(self, parent=None, host_name=None, filter_hosts=None):
        # Definition of experimental tools
        experimental_tools = [
            ExperimentalTool(
                "publisher",
                "New publisher",
                self._show_publisher,
                "Combined creation and publishing into one tool."
            )
        ]

        # --- Example tool (callback will just print on click) ---
        # def example_callback(*args):
        #     print("Triggered tool")
        #
        # experimental_tools = [
        #     ExperimentalTool(
        #         "example",
        #         "Example experimental tool",
        #         example_callback,
        #         "Example tool tooltip."
        #     )
        # ]

        # Try to get host name from env variable `AVALON_APP`
        if not host_name:
            host_name = os.environ.get("AVALON_APP")

        # Decide if filtering by host name should happen
        if filter_hosts is None:
            filter_hosts = host_name is not None

        if filter_hosts and not host_name:
            filter_hosts = False

        # Filter tools by host name
        if filter_hosts:
            experimental_tools = [
                tool
                for tool in experimental_tools
                if tool.is_available_for_host(host_name)
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
        self._parent_widget = parent

        self._publisher_tool = None

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
