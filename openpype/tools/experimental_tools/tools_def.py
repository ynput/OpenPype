from openpype.settings import get_local_settings

# Constant key under which local settings are stored
LOCAL_EXPERIMENTAL_KEY = "experimental_tools"


class ExperimentalTool:
    """Definition of experimental tool.

    Args:
        identifier (str): String identifier of tool (unique).
        label (str): Label shown in UI.
        callback (function): Callback for UI button.
        tooltip (str): Tooltip showed on button.
        hosts_filter (list): List of host names for which is tool available.
            Some tools may not be available in all hosts.
    """
    def __init__(self, identifier, label, callback, tooltip, hosts_filter=None):
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
        """Trigger registerd callback."""
        self.callback()


class ExperimentalTools:
    """Wrapper around experimental tools.

    To add/remove experimental tool just add/remove tool to
    `experimental_tools` variable in __init__ function.

    """
    def __init__(self, parent=None, host_name=None, filter_hosts=None):
        experimental_tools = [
            ExperimentalTool(
                "publisher",
                "New publisher",
                self._show_publisher,
                "Combined creation and publishing into one tool."
            )
        ]
        if filter_hosts is None:
            filter_hosts = host_name is not None

        if filter_hosts and not host_name:
            filter_hosts = False

        if filter_hosts:
            experimental_tools = [
                tool
                for tool in experimental_tools
                if tool.is_available_for_host(host_name)
            ]

        self.tools_by_identifier = {
            tool.identifier: tool
            for tool in experimental_tools
        }
        self.tools = experimental_tools
        self._parent_widget = parent

        self._publisher_tool = None

    def refresh_availability(self):
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
