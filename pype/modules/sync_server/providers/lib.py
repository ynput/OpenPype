from enum import Enum
from .gdrive import GDriveHandler


class Providers(Enum):
    LOCAL = 'studio'
    GDRIVE = 'gdrive'


class ProviderFactory:
    """
        Factory class as a creator of multiple cloud destination.
        Each new implementation needs to be registered and added to Providers
        enum.
    """
    def __init__(self):
        self.providers = {}
        self.creators = {}

    def register_provider(self, provider, creator, batch_limit):
        """
            Provide all necessary information for one specific remote provider
        :param provider: <string> - name of provider
        :param creator: <class> - class implementing AbstractProvider
        :param batch_limit: <int> - number of files that could be processed in
                                    one loop (based on provider API quota)
        :return: modifies self.providers
        """
        self.providers[provider] = (creator, batch_limit)

    def get_provider(self, provider, tree=None):
        """
            Returns new instance of provider client.
            'tree' is used for injecting already created memory structure,
            without it constructor of provider would need to calculate it
            from scratch, which could be expensive.
        :param provider: <string> 'gdrive','S3'
        :param tree: <dictionary> - folder paths to folder id structure
        :return: <implementation of AbstractProvider>
        """
        creator_info = self._get_creator_info(provider)

        return creator_info[0](tree)

    def get_provider_batch_limit(self, provider):
        """
            Each provider has some limit of files that could be  processed in
            one batch (loop step). It is not 'file' limit per se, but
            calculation based on API queries for provider.
            (For example 'gdrive' has 1000 queries for 100 sec, one file could
            be multiple queries (one for each level of path + check if file
            exists)
        :param provider: <string> 'gdrive','S3'
        :return:
        """
        info = self._get_creator_info(provider)
        return info[1]

    def _get_creator_info(self, provider):
        """
            Collect all necessary info for provider. Currently only creator
            class and batch limit
        :param provider:
        :return:
        """
        creator_info = self.providers.get(provider)
        if not creator_info:
            raise ValueError(
                "Provider {} not registered yet".format(provider))
        return creator_info


factory = ProviderFactory()
factory.register_provider('gdrive', GDriveHandler, 7)
