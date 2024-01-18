

class BatchPublisherController(object):

    def __init__(self):
        from openpype.hosts.batchpublisher.models.batch_publisher_model import \
            BatchPublisherModel
        self.model = BatchPublisherModel()

    @property
    def project(self):
        return self.model.project

    @project.setter
    def project(self, project):
        self.model.project = project

    @property
    def ingest_settings(self):
        return self.model.ingest_settings

    def populate_from_directory(self, directory):
        self.model.populate_from_directory(directory)

    def publish(self):
        self.model.publish()