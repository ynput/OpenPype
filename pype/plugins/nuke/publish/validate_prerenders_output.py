import os
import pyblish.api


@pyblish.api.log
class ValidatePrerendersOutput(pyblish.api.Validator):
    """Validates that the output directory for the write nodes exists"""

    families = ['write.prerender']
    hosts = ['nuke']
    label = 'Pre-renders output'

    def process(self, instance):
        path = os.path.dirname(instance[0]['file'].value())

        if 'output' not in path:
            name = instance[0].name()
            msg = 'Output directory for %s is not in an "output" folder.' % name

            raise ValueError(msg)
