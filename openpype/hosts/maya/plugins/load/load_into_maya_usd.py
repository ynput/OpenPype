# -*- coding: utf-8 -*-
import uuid

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


class MayaUsdProxyReferenceUsd(load.LoaderPlugin):
    """Add a USD Reference into mayaUsdProxyShape

    TODO: It'd be much easier if this loader would be capable of returning the
        available containers in the scene based on the AYON URLs inside a USD
        stage. That way we could potentially avoid the need the custom
        identifier, stay closer to USD native data and rely solely on the
        AYON:asset=blue,subset=modelMain,version=1 url

    """

    families = ["model", "usd", "pointcache", "animation"]
    representations = ["usd", "usda", "usdc", "usdz", "abc"]

    label = "USD Add Reference"
    order = -999
    icon = "code-fork"
    color = "orange"

    identifier_key = "openpype_identifier"

    def load(self, context, name=None, namespace=None, options=None):

        from pxr import Sdf

        selection = list(iter_ufe_usd_selection())
        if not selection:
            # Create a maya USD proxy with /root prim and add the reference
            import mayaUsd_createStageWithNewLayer
            from pxr import UsdGeom

            # Make sure we can load the plugin
            cmds.loadPlugin("mayaUsdPlugin", quiet=True)

            shape = mayaUsd_createStageWithNewLayer.createStageWithNewLayer()
            stage = mayaUsd.ufe.getStage('|world' + shape)
            prim_path = "/root"
            UsdGeom.Xform.Define(stage, prim_path)
            root_layer = stage.GetRootLayer()
            root_layer.defaultPrim = prim_path
            prim = stage.GetPrimAtPath(prim_path)
        else:
            assert len(selection) == 1, "Select only one PRIM please"
            ufe_path = selection[0]
            prim = mayaUsd.ufe.ufePathToPrim(ufe_path)

        if not prim:
            raise RuntimeError("Invalid primitive")

        # Define reference using Sdf.Reference so we can directly set custom
        # data for it
        path = get_representation_path_from_context(context)

        references = prim.GetReferences()

        # Add unique containerised data to the reference
        identifier = str(prim.GetPath()) + ":" + str(uuid.uuid4())
        identifier_data = {self.identifier_key: identifier}
        reference = Sdf.Reference(assetPath=path,
                                  customData=identifier_data)

        success = references.AddReference(reference)
        if not success:
            raise RuntimeError("Failed to add reference")

        # TODO: We should actually just use the data on the `Sdf.Reference`
        #   instead of on the USDPrim
        container = containerise_prim(
            prim,
            name=name,
            namespace=namespace or "",
            context=context,
            loader=self.__class__.__name__
        )

        return container

    def update(self, container, representation):
        # type: (dict, dict) -> None
        """Update container with specified representation."""

        from pxr import Sdf

        prim = container["prim"]
        path = get_representation_path(representation)
        for references, index in self._get_prim_references(prim):
            reference = references[index]
            new_reference = Sdf.Reference(
                assetPath=path,
                customData=reference.customData,
                layerOffset=reference.layerOffset,
                primPath=reference.primPath
            )
            references[index] = new_reference

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
        prim = container["prim"]

        # Pop the references from the prepended items list
        related_references = reversed(list(self._get_prim_references(prim)))
        for references, index in related_references:
            references.remove(references[index])

        prim.ClearCustomDataByKey("openpype")

    def _get_prim_references(self, prim):

        # Get a list of all prepended references
        for prim_spec in prim.GetPrimStack():
            if not prim_spec:
                continue

            if not prim_spec.hasReferences:
                continue

            prepended_items = prim_spec.referenceList.prependedItems
            for index, reference in enumerate(prepended_items):
                # Override the matching reference identifier
                # TODO: Make sure we only return the correct reference
                yield prepended_items, index
