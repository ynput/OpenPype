import unreal

avalon_detected = True
try:
    from avalon import api
    from avalon import unreal as avalon_unreal
except ImportError as exc:
    avalon_detected = False
    unreal.log_error("Avalon: cannot load avalon [ {} ]".format(exc))

if avalon_detected:
    api.install(avalon_unreal)


@unreal.uclass()
class AvalonIntegration(unreal.AvalonPythonBridge):
    @unreal.ufunction(override=True)
    def RunInPython_Popup(self):
        unreal.log_warning("Avalon: showing tools popup")
        if avalon_detected:
            avalon_unreal.show_tools_popup()

    @unreal.ufunction(override=True)
    def RunInPython_Dialog(self):
        unreal.log_warning("Avalon: showing tools dialog")
        if avalon_detected:
            avalon_unreal.show_tools_dialog()
