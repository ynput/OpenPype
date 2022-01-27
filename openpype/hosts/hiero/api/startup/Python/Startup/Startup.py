import traceback

# activate hiero from pype
import avalon.api
import openpype.hosts.hiero.api as phiero
avalon.api.install(phiero)

try:
    __import__("openpype.hosts.hiero.api")
    __import__("pyblish")

except ImportError as e:
    print(traceback.format_exc())
    print("pyblish: Could not load integration: %s " % e)

else:
    # Setup integration
    import openpype.hosts.hiero.api as phiero
    phiero.lib.setup()
