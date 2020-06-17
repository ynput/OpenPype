from pype.hosts import resolve


class CreateShotClip(resolve.Creator):
    """Publishable clip"""

    label = "Shot"
    family = "clip"
    icon = "film"
    defaults = ["Main"]

    presets = None

    def process(self):
        print(f"Project name: {self.project.GetName()}")
        print(f"Sequence name: {self.sequence.GetName()}")
        print(self.presets)
