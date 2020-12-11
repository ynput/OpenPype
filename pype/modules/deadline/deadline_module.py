from .. import PypeModule


class DeadlineModule(PypeModule):
    name = "deadline"

    def initialize(self, modules_settings):
        # This module is always enabled
        deadline_settings = modules_settings[self.name]
        self.enabled = deadline_settings["enabled"]
        self.deadline_url = deadline_settings["DEADLINE_REST_URL"]

    def get_global_environments(self):
        """Deadline global environments for pype implementation."""
        return {
            "DEADLINE_REST_URL": self.deadline_url
        }

    def connect_with_modules(self, *_a, **_kw):
        return
