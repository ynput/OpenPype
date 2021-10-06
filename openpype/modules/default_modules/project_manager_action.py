from openpype.modules import OpenPypeModule
from openpype_interfaces import ITrayAction


class ProjectManagerAction(OpenPypeModule, ITrayAction):
    label = "Project Manager (beta)"
    name = "project_manager"
    admin_action = True

    def initialize(self, modules_settings):
        enabled = False
        module_settings = modules_settings.get(self.name)
        if module_settings:
            enabled = module_settings.get("enabled", enabled)
        self.enabled = enabled

        # Tray attributes
        self.project_manager_window = None

    def tray_init(self):
        """Initialization in tray implementation of ITrayAction."""
        self.create_project_manager_window()

    def on_action_trigger(self):
        """Implementation for action trigger of ITrayAction."""
        self.show_project_manager_window()

    def create_project_manager_window(self):
        """Initializa Settings Qt window."""
        if self.project_manager_window:
            return
        from openpype.tools.project_manager import ProjectManagerWindow

        self.project_manager_window = ProjectManagerWindow()

    def show_project_manager_window(self):
        """Show project manager tool window.

        Raises:
            AssertionError: Window must be already created. Call
                `create_project_manager_window` before calling this method.
        """
        if not self.project_manager_window:
            raise AssertionError("Window is not initialized.")

        # Store if was visible
        was_minimized = self.project_manager_window.isMinimized()

        # Show settings gui
        self.project_manager_window.show()

        if was_minimized:
            self.project_manager_window.showNormal()

        # Pull window to the front.
        self.project_manager_window.raise_()
        self.project_manager_window.activateWindow()
