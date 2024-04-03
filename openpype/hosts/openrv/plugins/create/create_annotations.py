import qtawesome
import rv
import os
from openpype.client import get_subsets, get_versions, get_representations
from openpype.hosts.openrv.api.pipeline import get_containers, imprint_container
from openpype.hosts.openrv.api import lib
from openpype.pipeline import get_current_project_name, get_current_context
from openpype.pipeline import (
    AutoCreator,
    CreatedInstance,
)
from openpype.hosts.openrv.plugins.load.load_frames import FramesLoader
from openpype.client import get_asset_by_name
from openpype.hosts.openrv.api.ocio import (
    set_group_ocio_active_state,
    set_group_ocio_colorspace
)


class AnnotationCreator(AutoCreator):
    """Collect each drawn annotation over a loaded container as an annotation.
    """
    identifier = "annotation"
    family = "annotation"
    label = "Annotation"

    default_variant = "Main"

    create_allow_context_change = False

    def create(self, options=None):
        # We never create an instance since it's collected from user
        # drawn annotations
        pass

    def collect_instances(self):

        project_name = get_current_project_name()
        containers = list(get_containers())
        if not containers:
            if not rv.commands.sources():
                return
            self.build_context_from_sources()
            containers = list(get_containers())
        representation_ids = set(c["representation"] for c in containers)
        representations = get_representations(
            project_name, representation_ids=representation_ids
        )
        representations_by_id = {
            str(repre["_id"]): repre for repre in representations
        }

        with lib.maintained_view():
            for container in containers:
                self._collect_container(container,
                                        project_name,
                                        representations_by_id)

    def build_context_from_sources(self):
        for source in rv.commands.sources():
            filepath = source[0]
            source, ext = os.path.splitext(filepath)
            source = os.path.dirname(source)
            ext = ext[1:]

            context = {}
            context.update(get_current_context())
            context['asset'] = get_asset_by_name(context['project_name'], context['asset_name'])
            subsets = get_subsets(context['project_name'], asset_ids=[context['asset']['_id']])
            context.update(self.get_repre_from_subsets(subsets, context, source, ext))

            loaded_node = rv.commands.nodesOfType('RVFileSource')[0]
            colorspace_data = context["representation"].get("data", {}).get("colorspaceData")
            if colorspace_data:
                colorspace = colorspace_data["colorspace"]
                self.log.info(f"Setting colorspace: {colorspace}")
                group = rv.commands.nodeGroup(loaded_node)

                # Enable OCIO for the node and set the colorspace
                set_group_ocio_active_state(group, state=True)
                set_group_ocio_colorspace(group, colorspace)

            imprint_container(
                loaded_node,
                name=context['representation']['context']['subset'],
                namespace=context['representation']['context']['asset'],
                context=context,
                loader=FramesLoader.__name__
            )

    def get_repre_from_subsets(self, subsets, context, source, ext):
        for subset in subsets:
            context['subset'] = subset
            versions = get_versions(context['project_name'], subset_ids=[subset['_id']])
            for version in versions:
                context['version_repre'] = version
                repres = get_representations(context['project_name'], version_ids=[version['_id']])
                for repre in repres:
                    if source in repre['data']['path'] and repre['context']['ext'] == ext:
                        context['representation'] = repre
                        return context


    def _collect_container(self,
                           container,
                           project_name,
                           representations_by_id):

        node = container["node"]
        self.log.debug(f"Processing container node: {node}")

        # View this particular group to get its marked and annotated frames
        # TODO: This will only find annotations on the actual source group
        #   and not for e.g. the source in the `defaultSequence`.
        # For now it's easiest to enable 'Annotation > Configure > Draw On
        # Source If Possible' so that most annotations end up on source
        source_group = rv.commands.nodeGroup(node)
        rv.commands.setViewNode(source_group)
        annotated_frames = rv.extra_commands.findAnnotatedFrames()
        if not annotated_frames:
            return

        namespace = container["namespace"]
        repre_id = container["representation"]
        repre_doc = representations_by_id.get(repre_id)
        if not repre_doc:
            # This could happen if for example a representation was loaded
            # through the library loader
            self.log.warning(f"No representation found in database for "
                             f"container: {container}")
            return

        repre_context = repre_doc["context"]
        source_representation_asset = repre_context["asset"]
        source_representation_task = repre_context["task"]["name"]

        # QUESTION Do we want to do anything with marked frames?
        # for marked in marked_frames:
        #     print("MARKED ------------ ", container, marked, source_group)

        source_representation_asset_doc = get_asset_by_name(
            project_name=project_name,
            asset_name=source_representation_asset
        )

        subset_name = self.get_subset_name(
            variant= f"{namespace}",
            task_name=source_representation_task,
            asset_doc=source_representation_asset_doc,
            project_name=project_name,
        )

        data = {
            "tags": ["review", "ftrackreview"],
            "task": source_representation_task,
            "asset": source_representation_asset,
            "subset": subset_name,
            "label": subset_name,
            "publish": True,
            "review": True,
            "annotated_frame": annotated_frames,
            "version_context": repre_doc["context"],
            "node": node
        }

        instance = CreatedInstance(
            family=self.family,
            subset_name=data["subset"],
            data=data,
            creator=self
        )

        self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        # TODO: Implement storage of annotation instance settings
        #   Need to define where to store the annotation instance data.
        pass

    def get_icon(self):
        return qtawesome.icon("fa.comments", color="white")
