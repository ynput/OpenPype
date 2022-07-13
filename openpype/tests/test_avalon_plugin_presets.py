from openpype.pipeline import (
    install_host,
    LegacyCreator,
    register_creator_plugin,
    discover_creator_plugins,
)


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

    @staticmethod
    def install():
        register_creator_plugin(MyTestCreator)


def test_avalon_plugin_presets(monkeypatch, printer):
    install_host(Test)

    plugins = discover_creator_plugins()
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
