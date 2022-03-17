import os
import contextlib
import hou
import sys
from collections import deque

import pyblish.api
import openpype.api

from openpype.pipeline import get_representation_path
import openpype.hosts.houdini.api.usd as hou_usdlib
from openpype.hosts.houdini.api.lib import render_rop


class ExitStack(object):
    """Context manager for dynamic management of a stack of exit callbacks.

    For example:

        with ExitStack() as stack:
            files = [stack.enter_context(open(fname)) for fname in filenames]
            # All opened files will automatically be closed at the end of
            # the with statement, even if attempts to open files later
            # in the list raise an exception

    """

    def __init__(self):
        self._exit_callbacks = deque()

    def pop_all(self):
        """Preserve the context stack by transferring it to a new instance"""
        new_stack = type(self)()
        new_stack._exit_callbacks = self._exit_callbacks
        self._exit_callbacks = deque()
        return new_stack

    def _push_cm_exit(self, cm, cm_exit):
        """Helper to correctly register callbacks to __exit__ methods"""

        def _exit_wrapper(*exc_details):
            return cm_exit(cm, *exc_details)

        _exit_wrapper.__self__ = cm
        self.push(_exit_wrapper)

    def push(self, exit):
        """Registers a callback with the standard __exit__ method signature.

        Can suppress exceptions the same way __exit__ methods can.

        Also accepts any object with an __exit__ method (registering a call
        to the method instead of the object itself)

        """
        # We use an unbound method rather than a bound method to follow
        # the standard lookup behaviour for special methods
        _cb_type = type(exit)
        try:
            exit_method = _cb_type.__exit__
        except AttributeError:
            # Not a context manager, so assume its a callable
            self._exit_callbacks.append(exit)
        else:
            self._push_cm_exit(exit, exit_method)
        return exit  # Allow use as a decorator

    def callback(self, callback, *args, **kwds):
        """Registers an arbitrary callback and arguments.

        Cannot suppress exceptions.
        """

        def _exit_wrapper(exc_type, exc, tb):
            callback(*args, **kwds)

        # We changed the signature, so using @wraps is not appropriate, but
        # setting __wrapped__ may still help with introspection
        _exit_wrapper.__wrapped__ = callback
        self.push(_exit_wrapper)
        return callback  # Allow use as a decorator

    def enter_context(self, cm):
        """Enters the supplied context manager

        If successful, also pushes its __exit__ method as a callback and
        returns the result of the __enter__ method.
        """
        # We look up the special methods on the type to match the with
        # statement
        _cm_type = type(cm)
        _exit = _cm_type.__exit__
        result = _cm_type.__enter__(cm)
        self._push_cm_exit(cm, _exit)
        return result

    def close(self):
        """Immediately unwind the context stack"""
        self.__exit__(None, None, None)

    def __enter__(self):
        return self

    def __exit__(self, *exc_details):
        # We manipulate the exception state so it behaves as though
        # we were actually nesting multiple with statements
        frame_exc = sys.exc_info()[1]

        def _fix_exception_context(new_exc, old_exc):
            while 1:
                exc_context = new_exc.__context__
                if exc_context in (None, frame_exc):
                    break
                new_exc = exc_context
            new_exc.__context__ = old_exc

        # Callbacks are invoked in LIFO order to match the behaviour of
        # nested context managers
        suppressed_exc = False
        while self._exit_callbacks:
            cb = self._exit_callbacks.pop()
            try:
                if cb(*exc_details):
                    suppressed_exc = True
                    exc_details = (None, None, None)
            except Exception:
                new_exc_details = sys.exc_info()
                # simulate the stack of exceptions by setting the context
                _fix_exception_context(new_exc_details[1], exc_details[1])
                if not self._exit_callbacks:
                    raise
                exc_details = new_exc_details
        return suppressed_exc


@contextlib.contextmanager
def parm_values(overrides):
    """Override Parameter values during the context."""

    originals = []
    try:
        for parm, value in overrides:
            originals.append((parm, parm.eval()))
            parm.set(value)
        yield
    finally:
        for parm, value in originals:
            # Parameter might not exist anymore so first
            # check whether it's still valid
            if hou.parm(parm.path()):
                parm.set(value)


class ExtractUSDLayered(openpype.api.Extractor):

    order = pyblish.api.ExtractorOrder
    label = "Extract Layered USD"
    hosts = ["houdini"]
    families = ["usdLayered", "usdShade"]

    # Force Output Processors so it will always save any file
    # into our unique staging directory with processed Avalon paths
    output_processors = ["avalon_uri_processor", "stagingdir_processor"]

    def process(self, instance):

        self.log.info("Extracting: %s" % instance)

        staging_dir = self.staging_dir(instance)
        fname = instance.data.get("usdFilename")

        # The individual rop nodes are collected as "publishDependencies"
        dependencies = instance.data["publishDependencies"]
        ropnodes = [dependency[0] for dependency in dependencies]
        assert all(
            node.type().name() in {"usd", "usd_rop"} for node in ropnodes
        )

        # Main ROP node, either a USD Rop or ROP network with
        # multiple USD ROPs
        node = instance[0]

        # Collect any output dependencies that have not been processed yet
        # during extraction of other instances
        outputs = [fname]
        active_dependencies = [
            dep
            for dep in dependencies
            if dep.data.get("publish", True)
            and not dep.data.get("_isExtracted", False)
        ]
        for dependency in active_dependencies:
            outputs.append(dependency.data["usdFilename"])

        pattern = r"*[/\]{0} {0}"
        save_pattern = " ".join(pattern.format(fname) for fname in outputs)

        # Run a stack of context managers before we start the render to
        # temporarily adjust USD ROP settings for our publish output.
        rop_overrides = {
            # This sets staging directory on the processor to force our
            # output files to end up in the Staging Directory.
            "stagingdiroutputprocessor_stagingDir": staging_dir,
            # Force the Avalon URI Output Processor to refactor paths for
            # references, payloads and layers to published paths.
            "avalonurioutputprocessor_use_publish_paths": True,
            # Only write out specific USD files based on our outputs
            "savepattern": save_pattern,
        }
        overrides = list()
        with ExitStack() as stack:

            for ropnode in ropnodes:
                manager = hou_usdlib.outputprocessors(
                    ropnode,
                    processors=self.output_processors,
                    disable_all_others=True,
                )
                stack.enter_context(manager)

                # Some of these must be added after we enter the output
                # processor context manager because those parameters only
                # exist when the Output Processor is added to the ROP node.
                for name, value in rop_overrides.items():
                    parm = ropnode.parm(name)
                    assert parm, "Parm not found: %s.%s" % (
                        ropnode.path(),
                        name,
                    )
                    overrides.append((parm, value))

            stack.enter_context(parm_values(overrides))

            # Render the single ROP node or the full ROP network
            render_rop(node)

        # Assert all output files in the Staging Directory
        for output_fname in outputs:
            path = os.path.join(staging_dir, output_fname)
            assert os.path.exists(path), "Output file must exist: %s" % path

        # Set up the dependency for publish if they have new content
        # compared to previous publishes
        for dependency in active_dependencies:
            dependency_fname = dependency.data["usdFilename"]

            filepath = os.path.join(staging_dir, dependency_fname)
            similar = self._compare_with_latest_publish(dependency, filepath)
            if similar:
                # Deactivate this dependency
                self.log.debug(
                    "Dependency matches previous publish version,"
                    " deactivating %s for publish" % dependency
                )
                dependency.data["publish"] = False
            else:
                self.log.debug("Extracted dependency: %s" % dependency)
                # This dependency should be published
                dependency.data["files"] = [dependency_fname]
                dependency.data["stagingDir"] = staging_dir
                dependency.data["_isExtracted"] = True

        # Store the created files on the instance
        if "files" not in instance.data:
            instance.data["files"] = []
        instance.data["files"].append(fname)

    def _compare_with_latest_publish(self, dependency, new_file):

        from avalon import api, io
        import filecmp

        _, ext = os.path.splitext(new_file)

        # Compare this dependency with the latest published version
        # to detect whether we should make this into a new publish
        # version. If not, skip it.
        asset = io.find_one(
            {"name": dependency.data["asset"], "type": "asset"}
        )
        subset = io.find_one(
            {
                "name": dependency.data["subset"],
                "type": "subset",
                "parent": asset["_id"],
            }
        )
        if not subset:
            # Subset doesn't exist yet. Definitely new file
            self.log.debug("No existing subset..")
            return False

        version = io.find_one(
            {"type": "version", "parent": subset["_id"], },
            sort=[("name", -1)]
        )
        if not version:
            self.log.debug("No existing version..")
            return False

        representation = io.find_one(
            {
                "name": ext.lstrip("."),
                "type": "representation",
                "parent": version["_id"],
            }
        )
        if not representation:
            self.log.debug("No existing representation..")
            return False

        old_file = get_representation_path(representation)
        if not os.path.exists(old_file):
            return False

        return filecmp.cmp(old_file, new_file)
