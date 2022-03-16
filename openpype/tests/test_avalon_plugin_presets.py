import avalon.api as api
import openpype
from openpype.pipeline import LegacyCreator


class MyTestCreator(LegacyCreator):

    my_test_property = "A"

    def __init__(self, name, asset, options=None, data=None):
        super(MyTestCreator, self).__init__(self, name, asset,
                                            options=None, data=None)


# this is hack like no other - we need to inject our own avalon host
# and bypass all its validation. Avalon hosts are modules that needs
# `ls` callable as attribute. Voila:
class Test:
    __name__ = "test"
    ls = len

    def __call__(self):
        pass


def test_avalon_plugin_presets(monkeypatch, printer):

    openpype.install()
    api.register_host(Test())
    api.register_plugin(LegacyCreator, MyTestCreator)
    plugins = api.discover(LegacyCreator)
    printer("Test if we got our test plugin")
    assert MyTestCreator in plugins
    for p in plugins:
        if p.__name__ == "MyTestCreator":
            printer("Test if we have overridden existing property")
            assert p.my_test_property == "B"
            printer("Test if we have overridden superclass property")
            assert p.active is False
            printer("Test if we have added new property")
            assert p.new_property == "new"
