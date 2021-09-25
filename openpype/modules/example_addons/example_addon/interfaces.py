""" Using interfaces is one way of connecting multiple OpenPype Addons/Modules.

Interfaces must be in `interfaces.py` file (or folder). Interfaces should not
import module logic or other module in global namespace. That is because
all of them must be imported before all OpenPype AddOns and Modules.

Ideally they should just define abstract and helper methods. If interface
require any logic or connection it should be defined in module.

Keep in mind that attributes and methods will be added to other addon
attributes and methods so they should be unique and ideally contain
addon name in it's name.
"""

from abc import abstractmethod
from openpype.modules import OpenPypeInterface


class IExampleInterface(OpenPypeInterface):
    """Example interface of addon."""
    _example_module = None

    def get_example_module(self):
        return self._example_module

    @abstractmethod
    def example_method_of_example_interface(self):
        pass
