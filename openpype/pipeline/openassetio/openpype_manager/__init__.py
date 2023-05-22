from openassetio.pluginSystem import PythonPluginSystemManagerPlugin

class OpenPypeManagerPlugin(PythonPluginSystemManagerPlugin):
    @staticmethod
    def identifier():
        return "com.ftrack"

    @classmethod
    def interface(cls):
        # pylint: disable=import-outside-toplevel
        from .manager import OpenPypeInterface

        return OpenPypeInterface()

plugin = OpenPypeManagerPlugin
