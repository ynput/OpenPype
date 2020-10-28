import six
from abc import ABCMeta, abstractmethod


@six.add_metaclass(ABCMeta)
class PypeHook:

    def __init__(self):
        pass

    @abstractmethod
    def execute(self, *args, **kwargs):
        pass
