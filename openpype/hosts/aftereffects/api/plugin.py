from openpype.pipeline import LoaderPlugin
from .launch_logic import get_stub


class AfterEffectsLoader(LoaderPlugin):
    @staticmethod
    def get_stub():
        return get_stub()
