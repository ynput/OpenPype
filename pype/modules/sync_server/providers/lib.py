from enum import Enum
from .gdrive import GDriveHandler

class Providers(Enum):
    GDRIVE = 'gdrive'


class ProviderFactory:
    """
        Factory class as a creator of multiple cloud destination.
        Each new implementation needs to be registered and added to Providers
        enum.
    """
    def __init__(self):
        self.providers = {}

    def register_provider(self, provider, creator):
        self.providers[provider] = creator

    def get_provider(self, provider):
        creator = self.providers.get(provider)
        if not creator:
            raise ValueError("provider")

        return creator()

factory = ProviderFactory()
factory.register_provider('gdrive', GDriveHandler)
