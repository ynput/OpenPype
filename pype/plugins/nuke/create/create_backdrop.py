from avalon.nuke.pipeline import Creator


class CreateBackdrop(Creator):
    """Add Publishable Backdrop"""

    name = "nukenodes"
    label = "Create Backdrop"
    family = "nukenodes"
    icon = "file-archive-o"
    defaults = ["Main"]

    def __init__(self, *args, **kwargs):
        super(CreateBackdrop, self).__init__(*args, **kwargs)
        return
