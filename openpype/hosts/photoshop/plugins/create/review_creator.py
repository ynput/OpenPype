from openpype.hosts.photoshop.lib import PSAutoCreator


class PSReviewCreator(PSAutoCreator):
    """Creates review instance which might be disabled from publishing."""
    identifier = "review"
    family = "review"

    default_variant = "Main"
