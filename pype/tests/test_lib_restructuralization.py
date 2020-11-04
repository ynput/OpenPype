# Test for backward compability of restructure of lib.py into lib library
# #664
# Contains simple imports that should still work


def test_backward_compatibility(printer):
    printer("Test if imports still work")
    try:
        from pype.lib import filter_pyblish_plugins
        from pype.lib import execute_hook
        from pype.lib import PypeHook
    except ImportError as e:
        raise