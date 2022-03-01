import unreal

openpype_detected = True
try:
    from avalon import api
except ImportError as exc:
    api = None
    openpype_detected = False
    unreal.log_error("Avalon: cannot load Avalon [ {} ]".format(exc))

try:
    from openpype.hosts.unreal import api as openpype_host
except ImportError as exc:
    openpype_host = None
    openpype_detected = False
    unreal.log_error("OpenPype: cannot load OpenPype [ {} ]".format(exc))

if openpype_detected:
    api.install(openpype_host)


@unreal.uclass()
class OpenPypeIntegration(unreal.OpenPypePythonBridge):
    @unreal.ufunction(override=True)
    def RunInPython_Popup(self):
        unreal.log_warning("OpenPype: showing tools popup")
        if openpype_detected:
            openpype_host.show_tools_popup()

    @unreal.ufunction(override=True)
    def RunInPython_Dialog(self):
        unreal.log_warning("OpenPype: showing tools dialog")
        if openpype_detected:
            openpype_host.show_tools_dialog()
