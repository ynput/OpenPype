# -*- coding: utf-8 -*-
import contextlib

from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.pipeline.load import get_representation_path_from_context
from openpype.hosts.maya.api.usdlib import (
    containerise_prim,
    iter_ufe_usd_selection
)

from maya import cmds
import mayaUsd


@contextlib.contextmanager
def no_edit_mode(prim, restore_after=True):
    """Ensure MayaReference prim is not in edit mode during context"""
    pulled_node = mayaUsd.lib.PrimUpdaterManager.readPullInformation(prim)
    ufe_path = None
    try:
        # remove edit state if pulled
        if pulled_node:
            import mayaUsdUtils
            assert mayaUsdUtils.isPulledMayaReference(pulled_node)
            cmds.mayaUsdDiscardEdits(pulled_node)

            # Discarding the edits directly selects the prim
            # so we can get the UFE path from selection
            ufe_path = cmds.ls(selection=True, ufeObjects=True, long=True)[0]

        yield prim, ufe_path, pulled_node
    finally:
        if restore_after and pulled_node and ufe_path:
            cmds.mayaUsdEditAsMaya(ufe_path)


class MayaUsdProxyAddMayaReferenceLoader(load.LoaderPlugin):
    """Read USD data in a Maya USD Proxy

    TODO: It'd be much easier if this loader would be capable of returning the
        available containers in the scene based on the AYON URLs inside a USD
        stage. That way we could potentially avoid the need for custom metadata
        keys, stay closer to USD native data and rely solely on the
        AYON:asset=blue,subset=modelMain,version=1 url

    """

    families = ["*"]
    representations = ["*"]
    extensions = ["ma", "mb"]

    label = "USD Add Maya Reference"
    order = -998
    icon = "code-fork"
    color = "orange"

    identifier_key = "openpype_identifier"

    def load(self, context, name=None, namespace=None, options=None):

        selection = list(iter_ufe_usd_selection())
        assert len(selection) == 1, "Select only one PRIM please"
        ufe_path = selection[0]
        path = get_representation_path_from_context(context)

        import mayaUsdAddMayaReference

        namespace = "test"
        prim = mayaUsdAddMayaReference.createMayaReferencePrim(
            ufe_path,
            path,
            namespace,
            # todo: add more of the arguments
            # mayaReferencePrimName Nameprim_name,
            # groupPrim (3-tuple, group name, type and kind)
            # variantSet (2-tuple, variant set name and variant name)
        )
        if not prim:
            # Failed to add a reference
            raise RuntimeError(f"Failed to add a reference at {ufe_path}")

        containerise_prim(
            prim,
            name=name,
            namespace=namespace or "",
            context=context,
            loader=self.__class__.__name__
        )

        return prim

    def _update_reference_path(self, prim, filepath):
        """Update MayaReference prim 'mayaReference' in nearest prim spec"""

        from pxr import Sdf

        # We want to update the authored opinion in the right place, e.g.
        # within a VariantSet if it's authored there. We go through the
        # PrimStack to find the first prim spec that authors an opinion
        # on the 'mayaReference' attribute where we have permission to
        # change it. This could technically mean we're altering it in
        # layers that we might not want to (e.g. a published USD file?)
        stack = prim.GetPrimStack()
        for prim_spec in stack:
            if "mayaReference" not in prim_spec.attributes:
                # prim spec defines no opinion on mayaRefernce attribute?
                continue

            attr = prim_spec.attributes["mayaReference"]
            if attr.permission != Sdf.PermissionPublic:
                print(f"Not allowed to edit: {attr}")
                continue

            if filepath != attr.default:
                print(
                    f"Updating {attr.path} - {attr.default} -> {filepath}")
                attr.default = filepath

            # Attribute is either updated or already set to
            # the value in that layer
            return

        # Just define in the current edit layer?
        attr = prim.GetAttribute("mayaReference")
        attr.Set(filepath)

    def update(self, container, representation):
        # type: (dict, dict) -> None
        """Update container with specified representation."""

        prim = container["prim"]
        filepath = get_representation_path(representation)

        with no_edit_mode(prim):
            self._update_reference_path(prim, filepath)

        # Update representation id
        # TODO: Do this in prim spec where we update reference path?
        prim.SetCustomDataByKey(
            "openpype:representation", str(representation["_id"])
        )

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        # type: (dict) -> None
        """Remove loaded container."""

        from openpype.hosts.maya.api.usdlib import remove_spec

        prim = container["prim"]
        with no_edit_mode(prim, restore_after=False):
            for spec in prim.GetPrimStack():
                remove_spec(spec)
