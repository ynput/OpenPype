from avalon.nuke.pipeline import Creator


class CreateBackdrop(Creator):
    """Add Publishable Backdrop"""

    name = "backdrop"
    label = "Backdrop"
    family = "group"
    icon = "cube"
    defaults = ["Main"]

    def __init__(self, *args, **kwargs):
        super(CreateBackdrop, self).__init__(*args, **kwargs)

        return
