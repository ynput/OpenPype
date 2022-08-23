from .gdrive import GDriveHandler
from .dropbox import DropboxHandler
from .local_drive import LocalDriveHandler
from .sftp import SFTPHandler


class ProviderFactory:
    """
        Factory class as a creator of multiple cloud destination.
        Each new implementation needs to be registered and added to Providers
        enum.
    """
    def __init__(self):
        self.providers = {}  # {'PROVIDER_LABEL: {cls, int},..}

    def register_provider(self, provider, creator, batch_limit):
        """
            Provide all necessary information for one specific remote provider
        Args:
            provider (string): name of provider
            creator (class): class implementing AbstractProvider
            batch_limit (int): number of files that could be processed in
                                    one loop (based on provider API quota)
        Returns:
            modifies self.providers and self.sites
        """
        self.providers[provider] = (creator, batch_limit)

    def get_provider(self, provider, project_name, site_name,
                     tree=None, presets=None):
        """
            Returns new instance of provider client for specific site.
            One provider could have multiple sites.

            'tree' is used for injecting already created memory structure,
            without it constructor of provider would need to calculate it
            from scratch, which could be expensive.
        Args:
            provider (string):  'gdrive','S3'
            site_name (string): descriptor of site, different service accounts
                must have different site name
            project_name (string): different projects could have diff. sites
            tree (dictionary):  - folder paths to folder id structure
            presets (dictionary): config for provider and site (eg.
                "credentials_url"..)
        Returns:
            (implementation of AbstractProvider)
        """
        creator_info = self._get_creator_info(provider)
        # call init
        site = creator_info[0](project_name, site_name, tree, presets)

        return site

    def get_provider_batch_limit(self, provider):
        """
            Each provider has some limit of files that could be  processed in
            one batch (loop step). It is not 'file' limit per se, but
            calculation based on API queries for provider.
            (For example 'gdrive' has 1000 queries for 100 sec, one file could
            be multiple queries (one for each level of path + check if file
            exists)
        Args:
            provider (string): 'gdrive','S3'
        Returns:
        """
        info = self._get_creator_info(provider)
        return info[1]

    def get_provider_configurable_items(self, provider):
        """
            Returns dict of modifiable properties for 'provider'.

            Provider contains information which its properties and on what
            level could be override
        """
        provider_info = self._get_creator_info(provider)

        return provider_info[0].get_configurable_items()

    def get_provider_cls(self, provider_code):
        """
            Returns class object for 'provider_code' to run class methods on.
        """
        provider_info = self._get_creator_info(provider_code)

        return provider_info[0]

    def _get_creator_info(self, provider):
        """
            Collect all necessary info for provider. Currently only creator
            class and batch limit.
        Args:
            provider (string): 'gdrive' etc
        Returns:
            (tuple): (creator, batch_limit)
                creator is class of a provider (ex: GDriveHandler)
                batch_limit denotes how many files synced at single loop
                   its provided via 'register_provider' as its needed even
                   before provider class is initialized itself
                   (setting it as a class variable didn't work)
        """
        creator_info = self.providers.get(provider)
        if not creator_info:
            raise ValueError(
                "Provider {} not registered yet".format(provider))
        return creator_info


factory = ProviderFactory()
# this says that there is implemented provider with a label 'gdrive'
# there is implementing 'GDriveHandler' class
# 7 denotes number of files that could be synced in single loop - learned by
# trial and error
factory.register_provider(GDriveHandler.CODE, GDriveHandler, 7)
factory.register_provider(DropboxHandler.CODE, DropboxHandler, 10)
factory.register_provider(LocalDriveHandler.CODE, LocalDriveHandler, 50)
factory.register_provider(SFTPHandler.CODE, SFTPHandler, 20)
