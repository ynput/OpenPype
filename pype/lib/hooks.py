# -*- coding: utf-8 -*-
"""Package containing code for handling hooks."""
import os
import sys
import types
import logging
from abc import ABCMeta, abstractmethod

import six


log = logging.getLogger(__name__)


@six.add_metaclass(ABCMeta)
class PypeHook:
    """Abstract class from all hooks should inherit."""

    def __init__(self):
        """Constructor."""
        pass

    @abstractmethod
    def execute(self, *args, **kwargs):
        """Abstract execute method."""
        pass


def execute_hook(hook, *args, **kwargs):
    """Execute hook with arguments.

    This will load hook file, instantiate class and call
    :meth:`PypeHook.execute` method on it. Hook must be in a form::

        $PYPE_SETUP_PATH/repos/pype/path/to/hook.py/HookClass

    This will load `hook.py`, instantiate HookClass and then execute_hook
    `execute(*args, **kwargs)`

    Args:
        hook (str): path to hook class.

    """
    class_name = hook.split("/")[-1]

    abspath = os.path.join(os.getenv('PYPE_SETUP_PATH'),
                           'repos', 'pype', *hook.split("/")[:-1])

    mod_name, mod_ext = os.path.splitext(os.path.basename(abspath))

    if not mod_ext == ".py":
        return False

    module = types.ModuleType(mod_name)
    module.__file__ = abspath

    try:
        with open(abspath) as f:
            six.exec_(f.read(), module.__dict__)

        sys.modules[abspath] = module

    except Exception as exp:
        log.exception("loading hook failed: {}".format(exp),
                      exc_info=True)
        return False

    obj = getattr(module, class_name)
    hook_obj = obj()
    ret_val = hook_obj.execute(*args, **kwargs)
    return ret_val
