import logging
import argparse

import avalon.io as io
import avalon.api as api
import avalon.fusion


log = logging.getLogger("UpdateSlapComp")


def switch(data, targets=None):
    """Update comp loaders through the containers

    Args:
        data (dict): collection if {asset: [subset, subset]}
        targets (list): to be implemented
    """

    representations = []

    for asset_name, subsets in data.iteritems():

        asset = io.find_one({"type": "asset", "name": asset_name})
        assert asset, ("Could not find asset in the database with the name "
                       "'%s'" % asset_name)

        subsets = io.find({"type": "subset",
                           "name": {"$in": subsets},
                           "parent": asset["_id"]})

        for subset in subsets:
            version = io.find_one({"type": "version",
                                   "parent": subset["_id"]},
                                  sort=[('name', -1)])

            if not version:
                log.error("Could not find a verison for {}.{}".format(
                    asset["name"], subset["name"]
                ))
                continue

            representation = io.find_one({"type": "representation",
                                          "parent": version["_id"]})

            representations.append(representation)

    host = api.registered_host()
    containers = list(host.ls())
    count = 0
    for i, container in enumerate(containers):
        representation = representations[i]
        api.switch(container, representation)
        count += 1

    log.info("Updated %i items" % count)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument("--data",
                        help="Dictionary with asset name as key and related "
                             "subsets (list) as value")

    parser.add_argument("--targets",
                        optional=True,
                        help="A list of target to update with given data")

    args = parser.parse_known_args()
    if not args.data:
        raise RuntimeError("No data given, cannot update slap comp")

    if not isinstance(args.data, dict):
        raise ValueError("Expecting data in the form of a dict, got "
                         "%s" % type(args.data))

    api.install(avalon.fusion)
    switch(data=args.data)
