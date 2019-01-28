import pyblish.api
import pype.api
import os

from collections import defaultdict


class ValidateTransfers(pyblish.api.InstancePlugin):
    """Validates mapped resources.

    This validates:
        - The resources all transfer to a unique destination.

    """

    order = pype.api.ValidateContentsOrder
    label = "Transfers"

    def process(self, instance):

        transfers = instance.data.get("transfers", [])
        if not transfers:
            return

        # Collect all destination with its sources
        collected = defaultdict(set)
        for source, destination in transfers:

            # Use normalized paths in comparison and ignore case sensitivity
            source = os.path.normpath(source).lower()
            destination = os.path.normpath(destination).lower()

            collected[destination].add(source)

        invalid_destinations = list()
        for destination, sources in collected.items():
            if len(sources) > 1:
                invalid_destinations.append(destination)

                self.log.error("Non-unique file transfer for resources: "
                               "{0} (sources: {1})".format(destination,
                                                           list(sources)))

        if invalid_destinations:
            raise RuntimeError("Invalid transfers in queue.")
