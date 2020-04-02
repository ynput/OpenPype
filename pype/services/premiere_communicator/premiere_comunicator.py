import os


class PremiereCommunicator:
    def tray_start(self):
        return

    def process_modules(self, modules):
        rest_api_module = modules.get("RestApiServer")
        if rest_api_module:
            self.rest_api_registration(rest_api_module)

    def rest_api_registration(self, module):
        static_site_dir_path = os.path.join(
            os.environ["PYPE_MODULE_ROOT"],
            "pype",
            "premiere",
            "ppro"
        ).replace("\\", "/")
        module.register_statics("/ppro", static_site_dir_path)
