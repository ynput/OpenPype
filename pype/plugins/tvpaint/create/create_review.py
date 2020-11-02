from avalon.tvpaint import pipeline, CommunicationWrapper


class CreateReview(pipeline.TVPaintCreator):
    """Arnold Archive"""

    name = "review"
    label = "Review"
    family = "review"
    icon = "cube"
    defaults = ["Main"]

    def process(self):
        instances = pipeline.list_instances()
        for instance in instances:
            if instance["family"] == self.family:
                self.log.info("Review family is already Created.")
                return
        super(CreateReview, self).process()
