class SaveSettingsValidation(Exception):
    pass


class SaveWarning(SaveSettingsValidation):
    def __init__(self, warnings):
        if isinstance(warnings, str):
            warnings = [warnings]
        self.warnings = warnings
        msg = ", ".join(warnings)
        super(SaveWarning, self).__init__(msg)
