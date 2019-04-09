
# import pype.api as pype

import pyblish.api
from pypeapp import Anatomy
import os


class CollectTemplates(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder
    label = "Collect Templates"

    def process(self, context):
        # pype.load_data_from_templates()

        anatomy = Anatomy(project_name=os.environ.get("AVALON_PROJECT"))
        context.data['anatomy'] = anatomy
        self.log.info("Anatomy templates collected...")
