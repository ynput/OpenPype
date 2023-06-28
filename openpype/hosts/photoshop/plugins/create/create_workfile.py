from openpype.hosts.photoshop.lib import PSAutoCreator


class WorkfileCreator(PSAutoCreator):
    identifier = "workfile"
    family = "workfile"

    default_variant = "Main"

    def get_detail_description(self):
        return """Auto creator for workfile.

        It is expected that each publish will also publish its source workfile
        for safekeeping. This creator triggers automatically without need for
        an artist to remember and trigger it explicitly.

        Workfile instance could be disabled if it is not required to publish
        workfile. (Instance shouldn't be deleted though as it will be recreated
        in next publish automatically).
        """

    def apply_settings(self, project_settings, system_settings):
        plugin_settings = (
            project_settings["photoshop"]["create"]["WorkfileCreator"]
        )

        self.active_on_create = plugin_settings["active_on_create"]
        self.enabled = plugin_settings["enabled"]
