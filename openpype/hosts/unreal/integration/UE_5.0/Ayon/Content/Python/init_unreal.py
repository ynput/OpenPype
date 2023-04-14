import unreal

ayon_detected = True
try:
    from openpype.pipeline import install_host
    from openpype.hosts.unreal.api import UnrealHost

    ayon_host = UnrealHost()
except ImportError as exc:
    ayon_host = None
    ayon_detected = False
    unreal.log_error(f"Ayon: cannot load Ayon integration [ {exc} ]")

if ayon_detected:
    install_host(ayon_host)


@unreal.uclass()
class AyonIntegration(unreal.AyonPythonBridge):
    @unreal.ufunction(override=True)
    def RunInPython_Popup(self):
        unreal.log_warning("Ayon: showing tools popup")
        if ayon_detected:
            ayon_host.show_tools_popup()

    @unreal.ufunction(override=True)
    def RunInPython_Dialog(self):
        unreal.log_warning("Ayon: showing tools dialog")
        if ayon_detected:
            ayon_host.show_tools_dialog()
