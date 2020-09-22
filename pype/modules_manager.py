import os
import inspect

import pype.modules
from pype.modules import PypeModule
from pype.settings import system_settings
from pype.api import Logger


class PypeModuleManager:
    skip_module_names = ("__pycache__", )

    def __init__(self):
        self.log = Logger().get_logger(
            "{}.{}".format(__name__, self.__class__.__name__)
        )

        self.pype_modules = self.find_pype_modules()

    def modules_environments(self):
        environments = {}
        for pype_module in self.pype_modules.values():
            environments.update(pype_module.startup_environments())
        return environments

    def find_pype_modules(self):
        settings = system_settings()
        modules = []
        dirpath = os.path.dirname(pype.modules.__file__)
        for module_name in os.listdir(dirpath):
            # Check if path lead to a folder
            full_path = os.path.join(dirpath, module_name)
            if not os.path.isdir(full_path):
                continue

            # Skip known invalid names
            if module_name in self.skip_module_names:
                continue

            import_name = "pype.modules.{}".format(module_name)
            try:
                modules.append(
                    __import__(import_name, fromlist=[""])
                )

            except Exception:
                self.log.warning(
                    "Couldn't import {}".format(import_name), exc_info=True
                )

        pype_module_classes = []
        for module in modules:
            try:
                pype_module_classes.extend(
                    self._classes_from_module(PypeModule, module)
                )
            except Exception:
                self.log.warning(
                    "Couldn't import {}".format(import_name), exc_info=True
                )

        pype_modules = {}
        for pype_module_class in pype_module_classes:
            try:
                pype_module = pype_module_class(settings)
                if pype_module.enabled:
                    pype_modules[pype_module.id] = pype_module
            except Exception:
                self.log.warning(
                    "Couldn't create instance of {}".format(
                        pype_module_class.__class__.__name__
                    ),
                    exc_info=True
                )
        return pype_modules

    def _classes_from_module(self, superclass, module):
        classes = list()

        def recursive_bases(klass):
            output = []
            output.extend(klass.__bases__)
            for base in klass.__bases__:
                output.extend(recursive_bases(base))
            return output

        for name in dir(module):
            # It could be anything at this point
            obj = getattr(module, name)

            if not inspect.isclass(obj) or not len(obj.__bases__) > 0:
                continue

            # Use string comparison rather than `issubclass`
            # in order to support reloading of this module.
            bases = recursive_bases(obj)
            if not any(base.__name__ == superclass.__name__ for base in bases):
                continue

            classes.append(obj)

        return classes
