# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

from ._version import __version__
from .session import Session


def mixin(instance, mixin_class, name=None):
    '''Mixin *mixin_class* to *instance*.

    *name* can be used to specify new class name. If not specified then one will
    be generated.

    '''
    if name is None:
        name = '{0}{1}'.format(
            instance.__class__.__name__, mixin_class.__name__
        )

    # Check mixin class not already present in mro in order to avoid consistent
    # method resolution failure.
    if mixin_class in instance.__class__.mro():
        return

    instance.__class__ = type(
        name,
        (
            mixin_class,
            instance.__class__
        ),
        {}
    )
