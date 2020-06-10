from avalon import photoshop


class CreateImage(photoshop.Creator):
    """Image folder for publish."""

    name = "imageDefault"
    label = "Image"
    family = "image"

    def __init__(self, *args, **kwargs):
        super(CreateImage, self).__init__(*args, **kwargs)
