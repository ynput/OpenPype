import copy


class ServerEvent(object):
    def __init__(
        self,
        topic,
        sender=None,
        event_hash=None,
        project_name=None,
        username=None,
        dependencies=None,
        description=None,
        summary=None,
        payload=None,
        finished=True,
        store=True,
    ):
        if dependencies is None:
            dependencies = []
        if payload is None:
            payload = {}
        if summary is None:
            summary = {}

        self.topic = topic
        self.sender = sender
        self.event_hash = event_hash
        self.project_name = project_name
        self.username = username
        self.dependencies = dependencies
        self.description = description
        self.summary = summary
        self.payload = payload
        self.finished = finished
        self.store = store

    def to_data(self):
        return {
            "topic": self.topic,
            "sender": self.sender,
            "hash": self.event_hash,
            "project": self.project_name,
            "user": self.username,
            "dependencies": copy.deepcopy(self.dependencies),
            "description": self.description,
            "description": self.description,
            "summary": copy.deepcopy(self.summary),
            "payload": self.payload,
            "finished": self.finished,
            "store": self.store
        }
