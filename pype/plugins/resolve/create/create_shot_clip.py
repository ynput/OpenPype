import avalon.api
from pype.hosts import resolve


class CreateShotClip(avalon.api.Creator):
    """Publishable clip"""

    label = "Shot"
    family = "clip"
    icon = "film"
    defaults = ["Main"]

    def process(self):
        project = resolve.get_current_project()
        self.log.info(f"Project name: {project.GetName()}")
