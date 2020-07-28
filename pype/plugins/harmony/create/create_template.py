from avalon import harmony


class CreateTemplate(harmony.Creator):
    """Composite node for publishing to templates."""

    name = "templateDefault"
    label = "Template"
    family = "harmony.template"

    def __init__(self, *args, **kwargs):
        super(CreateTemplate, self).__init__(*args, **kwargs)
