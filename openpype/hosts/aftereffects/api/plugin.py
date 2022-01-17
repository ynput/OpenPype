import avalon.api
from .launch_logic import get_stub


class AfterEffectsLoader(avalon.api.Loader):
    @staticmethod
    def get_stub():
        return get_stub()

