import traceback

# activate hiero from pype
import avalon.api
import pype.hosts.hiero
avalon.api.install(pype.hosts.hiero)

try:
    __import__("pype.hosts.hiero")
    __import__("pyblish")

except ImportError as e:
    print traceback.format_exc()
    print("pyblish: Could not load integration: %s " % e)

else:
    # Setup integration
    import pype.hosts.hiero.lib
    pype.hosts.hiero.lib.setup()
