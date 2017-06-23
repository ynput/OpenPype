import os
from collections import defaultdict

import pyblish.api
import colorbleed.api

import cbra.lib
from cbra.utils.maya.abc import get_alembic_ids
from cbra.utils.maya.node_uuid import get_id


def get_subset_path(context):
    return os.path.join(context['itemPath'],
                        cbra.lib.DIR_PUBLISH,
                        context['family'],
                        context['subset'])


class ValidateUniqueIdsInItem(pyblish.api.InstancePlugin):
    """Checks whether IDs are unique across other subsets
    
    This ensures a model to be published can't have ids 
    which are already present in another subset. For example
    the "default" model can't have ids present in the "high"
    subset.
    
    Note:
        This will also invalidate the instance if it contains
        nodes that are present in another instance in the scene.
        So ensure the instance you're publishing actually has
        the correct set members.
        
    """

    order = colorbleed.api.ValidateMeshOrder
    families = ['colorbleed.model']
    hosts = ['maya']
    label = 'Unique Ids in Item'
    actions = [colorbleed.api.SelectInvalidAction]
    optional = True

    @classmethod
    def iter_invalid(cls, instance):

        verbose = instance.data.get("verbose", False)

        def _get_instance_ids(instance):
            """Collect ids in an instance"""
            nodes_per_id = defaultdict(list)
            for node in instance:
                node_id = get_id(node)
                if node_id:
                    nodes_per_id[node_id].append(node)
            return nodes_per_id

        nodes_per_id = _get_instance_ids(instance)
        if not nodes_per_id:
            return

        ids_lookup = set(nodes_per_id.keys())

        instance_context = instance.data["instanceContext"]
        instance_subset = instance.data['subset']

        assert instance_context, "Instance must have 'instanceContext' data"
        assert instance_subset, "Instance must have 'subset' data"

        subsets_checked = set()
        subsets_checked.add(instance_subset)  # we can skip this subset

        # Compare with all other *currently publishing instances*
        # of family 'model' for this item
        for other_instance in instance.context:
            if other_instance is instance:
                continue

            if other_instance.data['subset'] == instance_subset:
                cls.log.error("Another instance has the same subset? "
                              "This should never happen.")

            if other_instance.data['family'] != "model":
                continue

            if other_instance.data['instanceContext']['item'] != \
                    instance_context['item']:
                cls.log.error("Also publishing model for other item? "
                              "This should never happen.")
                continue
            other_ids = _get_instance_ids(other_instance).keys()

            # Perform comparison
            intersection = ids_lookup.intersection(other_ids)
            if intersection:
                for node_id in intersection:
                    nodes = nodes_per_id[node_id]
                    for node in nodes:
                        yield node

                # Those that are invalid don't need to be checked again
                ids_lookup.difference_update(other_ids)

            if not ids_lookup:
                # Once we have no ids to check for anymore we can already
                # return
                return

            subsets_checked.add(other_instance.data['subset'])

        # Compare with all previously *published instances*
        # of family 'model' for this item
        ctx = instance_context.copy()
        ctx['family'] = "model"

        published_subsets = cbra.lib.list_subsets(ctx)
        published_subsets = set(x for x in published_subsets if
                                x != instance_subset)

        for published_subset in published_subsets:
            ctx['subset'] = published_subset
            ctx['subsetPath'] = get_subset_path(ctx)

            versions = cbra.lib.list_versions(ctx)
            version = cbra.lib.find_highest_version(versions)
            if not version:
                cls.log.debug("No published version for "
                              "'model': {0}".format(published_subset))
                continue

            ctx['currentVersion'] = version
            publish_abc = cbra.lib.get_filepath(ctx) + ".abc"

            if not os.path.exists(publish_abc):
                cls.log.error("Published file to compare with does not exist: "
                              "{0}".format(publish_abc))
                continue

            if verbose:
                cls.log.debug("Comparing with: {0}".format(publish_abc))

            abc_ids = set(get_alembic_ids(publish_abc).values())

            # Perform comparison
            intersection = ids_lookup.intersection(abc_ids)
            if intersection:
                for node_id in intersection:
                    nodes = nodes_per_id[node_id]
                    for node in nodes:
                        yield node

                # Those that are invalid don't need to be checked again
                ids_lookup.difference_update(abc_ids)

            if not ids_lookup:
                # Once we have no ids to check for anymore we can already
                # return
                return

        return

    @classmethod
    def get_invalid(cls, instance):
        return list(cls.iter_invalid(instance))

    def process(self, instance):
        """Process all meshes"""
        if any(self.iter_invalid(instance)):
            raise RuntimeError("Invalid nodes found in {0}".format(instance))
