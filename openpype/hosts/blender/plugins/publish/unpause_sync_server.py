from concurrent.futures import as_completed
import re

import pyblish

from openpype.modules.base import ModulesManager
from openpype.modules.timers_manager.plugins.publish.start_timer import (
    StartTimer,
)

BUILTIN_EXCEPTIONS = {
    "BaseException",
    "GeneratorExit",
    "KeyboardInterrupt",
    "SystemExit",
    "Exception",
    "ArithmeticError",
    "FloatingPointError",
    "OverflowError",
    "ZeroDivisionError",
    "AssertionError",
    "AttributeError",
    "BufferError",
    "EOFError",
    "ImportError",
    "ModuleNotFoundError",
    "LookupError",
    "IndexError",
    "KeyError",
    "MemoryError",
    "NameError",
    "UnboundLocalError",
    "OSError",
    "BlockingIOError",
    "ChildProcessError",
    "ConnectionError",
    "BrokenPipeError",
    "ConnectionAbortedError",
    "ConnectionRefusedError",
    "ConnectionResetError",
    "FileExistsError",
    "FileNotFoundError",
    "InterruptedError",
    "IsADirectoryError",
    "NotADirectoryError",
    "PermissionError",
    "ProcessLookupError",
    "TimeoutError",
    "ReferenceError",
    "RuntimeError",
    "NotImplementedError",
    "RecursionError",
    "StopAsyncIteration",
    "StopIteration",
    "SyntaxError",
    "IndentationError",
    "TabError",
    "SystemError",
    "TypeError",
    "ValueError",
    "UnicodeError",
    "UnicodeDecodeError",
    "UnicodeEncodeError",
    "UnicodeTranslateError",
    "Warning",
    "BytesWarning",
    "DeprecationWarning",
    "EncodingWarning",
    "FutureWarning",
    "ImportWarning",
    "PendingDeprecationWarning",
    "ResourceWarning",
    "RuntimeWarning",
    "SyntaxWarning",
    "UnicodeWarning",
    "UserWarning",
}


def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)]
    )


class UnpauseSyncServer(pyblish.api.ContextPlugin):
    label = "Unpause Sync Server"
    hosts = ["blender"]
    order = StartTimer.order

    def process(self, context):
        manager = ModulesManager()
        sync_server_module = manager.modules_by_name["sync_server"]
        sync_server_module.unpause_server()

        # Compile match patterns
        match_tb = re.compile(
            "|".join(f"Traceback.*{e}: .*?\n" for e in BUILTIN_EXCEPTIONS),
            re.DOTALL,
        )
        match_blend_file = re.compile("Read blend:(.*)")

        # Wait for all started futures to finish
        subprocess_errors = False
        for instance in context:
            for future in as_completed(
                instance.data.get("representations_futures", [])
            ):
                result = future.result().decode()

                # Iterate through matched errors
                if errors_stack := re.finditer(match_tb, result):
                    # Match file path
                    blend_file = re.search(match_blend_file, result)

                    # Notify matched erros in log
                    for stack in errors_stack:
                        self.log.error(
                            f"Blend file: {blend_file[1]}\n\n{stack[0]}"
                        )
                    subprocess_errors = True
                else:
                    self.log.info(result)

        # Stop if errors
        if subprocess_errors:
            raise RuntimeError(
                "Errors occured during subprocesses. See above."
            )
