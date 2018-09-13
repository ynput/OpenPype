import pyblish.api
import colorbleed.api
import os

from collections import defaultdict


class ValidateTransfers(pyblish.api.InstancePlugin):
    """Validates mapped resources.

    This validates:
        - The resources all transfer to a unique destination.

    """

    order = colorbleed.api.ValidateContentsOrder
    label = "Transfers"

    def process(self, instance):

        transfers = instance.data.get("transfers", [])
        if not transfers:
            return

        verbose = instance.data.get('verbose', False)

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

                if verbose:
                    self.log.error("Non-unique file transfer for resources: "
                                   "{0} (sources: {1})".format(destination,
                                                               sources))

        if invalid_destinations:
            if not verbose:
                # If not verbose then still log the resource destination as
                # opposed to every individual file transfer
                self.log.error("Non-unique file transfers to destinations: "
                               "%s" % "\n".join(invalid_destinations))

            raise RuntimeError("Invalid transfers in queue.")
