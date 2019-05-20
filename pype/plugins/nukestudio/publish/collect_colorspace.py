import pyblish.api


class CollectProjectColorspace(pyblish.api.ContextPlugin):
    """get active project color settings"""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Project's color settings"
    def process(self, context):
        import hiero

        project = context.data["activeProject"]
        colorspace = {}
        colorspace["useOCIOEnvironmentOverride"] = project.useOCIOEnvironmentOverride()
        colorspace["lutSetting16Bit"] = project.lutSetting16Bit()
        colorspace["lutSetting8Bit"] = project.lutSetting8Bit()
        colorspace["lutSettingFloat"] = project.lutSettingFloat()
        colorspace["lutSettingLog"] = project.lutSettingLog()
        colorspace["lutSettingViewer"] = project.lutSettingViewer()
        colorspace["lutSettingWorkingSpace"] = project.lutSettingWorkingSpace()
        colorspace["lutUseOCIOForExport"] = project.lutUseOCIOForExport()
        colorspace["ocioConfigName"] = project.ocioConfigName()
        colorspace["ocioConfigPath"] = project.ocioConfigPath()

        context.data["colorspace"] = colorspace

        self.log.info("context.data[colorspace]: {}".format(context.data["colorspace"]))
