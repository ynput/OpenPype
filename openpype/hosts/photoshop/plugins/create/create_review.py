from openpype.hosts.photoshop.lib import PSAutoCreator


class ReviewCreator(PSAutoCreator):
    """Creates review instance which might be disabled from publishing."""
    identifier = "review"
    family = "review"

    default_variant = "Main"

    def get_detail_description(self):
        return """Auto creator for review.

        Photoshop review is created from all published images or from all
        visible layers if no `image` instances got created.

        Review might be disabled by an artist (instance shouldn't be deleted as
        it will get recreated in next publish either way).
        """

    def apply_settings(self, project_settings):
        plugin_settings = (
            project_settings["photoshop"]["create"]["ReviewCreator"]
        )

        self.default_variant = plugin_settings["default_variant"]
        self.active_on_create = plugin_settings["active_on_create"]
        self.enabled = plugin_settings["enabled"]
