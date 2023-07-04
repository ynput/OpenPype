from concurrent.futures import as_completed
import re

import pyblish

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
REGEX_BUILTIN_EXCEPTIONS = re.compile(
    "|".join(f"Traceback.*{e}: .*?\n" for e in BUILTIN_EXCEPTIONS), re.DOTALL
)
REGEX_BLEND_FILE = re.compile("Read blend:(.*)")


class UnpauseSyncServer(pyblish.api.ContextPlugin):
    label = "Unpause Sync Server"
    hosts = ["blender"]
    order = StartTimer.order

    def process(self, context):
        project_name = context.data["projectEntity"]["name"]
        sync_server_module = context.data["openPypeModules"]["sync_server"]
        sync_server_module.unpause_project(project_name)

        # Wait for all started futures to finish
        subprocess_errors = False
        for future in as_completed(
            context.data.get("representations_futures", [])
        ):
            result = future.result().decode()

            # Iterate through matched errors
            if errors_stack := list(
                re.finditer(REGEX_BUILTIN_EXCEPTIONS, result)
            ):
                # Match file path
                blend_file = re.search(REGEX_BLEND_FILE, result)

                # Notify matched erros in log
                for stack in errors_stack:
                    self.log.error(
                        f"Blend file: {blend_file[1]}\n\n{stack[0]}\n"
                        f"~~~~~\n\n{result}"
                    )
                subprocess_errors = True
            else:
                self.log.info(result)

        # Stop if errors
        if subprocess_errors:
            raise RuntimeError(
                "Errors occured during subprocesses. See above."
            )
