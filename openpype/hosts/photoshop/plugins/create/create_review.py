from openpype.hosts.photoshop.lib import PSAutoCreator


class ReviewCreator(PSAutoCreator):
    """Creates review instance which might be disabled from publishing."""
    identifier = "review"
    family = "review"

    default_variant = "Main"
