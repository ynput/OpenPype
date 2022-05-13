import os

import unreal

from openpype.api import Anatomy
from openpype.hosts.unreal.api import pipeline


queue = None
executor = None


def _queue_finish_callback(exec, success):
    unreal.log("Render completed. Success: " + str(success))

    # Delete our reference so we don't keep it alive.
    global executor
    global queue
    del executor
    del queue


def _job_finish_callback(job, success):
    # You can make any edits you want to the editor world here, and the world
    # will be duplicated when the next render happens. Make sure you undo your
    # edits in OnQueueFinishedCallback if you don't want to leak state changes
    # into the editor world.
    unreal.log("Individual job completed.")


def start_rendering():
    """
    Start the rendering process.
    """
    print("Starting rendering...")

    # Get selected sequences
    assets = unreal.EditorUtilityLibrary.get_selected_assets()

    # instances = pipeline.ls_inst()
    instances = [
        a for a in assets
        if a.get_class().get_name() == "OpenPypePublishInstance"]

    inst_data = []

    for i in instances:
        data = pipeline.parse_container(i.get_path_name())
        if data["family"] == "render":
            inst_data.append(data)

    try:
        project = os.environ.get("AVALON_PROJECT")
        anatomy = Anatomy(project)
        root = anatomy.roots['renders']
    except Exception:
        raise Exception("Could not find render root in anatomy settings.")

    render_dir = f"{root}/{project}"

    # subsystem = unreal.get_editor_subsystem(
    #     unreal.MoviePipelineQueueSubsystem)
    # queue = subsystem.get_queue()
    global queue
    queue = unreal.MoviePipelineQueue()

    ar = unreal.AssetRegistryHelpers.get_asset_registry()

    for i in inst_data:
        sequence = ar.get_asset_by_object_path(i["sequence"]).get_asset()

        sequences = [{
            "sequence": sequence,
            "output": f"{i['output']}",
            "frame_range": (
                int(float(i["frameStart"])),
                int(float(i["frameEnd"])) + 1)
        }]
        render_list = []

        # Get all the sequences to render. If there are subsequences,
        # add them and their frame ranges to the render list. We also
        # use the names for the output paths.
        for s in sequences:
            subscenes = pipeline.get_subsequences(s.get('sequence'))

            if subscenes:
                for ss in subscenes:
                    sequences.append({
                        "sequence": ss.get_sequence(),
                        "output": (f"{s.get('output')}/"
                                   f"{ss.get_sequence().get_name()}"),
                        "frame_range": (
                            ss.get_start_frame(), ss.get_end_frame())
                    })
            else:
                # Avoid rendering camera sequences
                if "_camera" not in s.get('sequence').get_name():
                    render_list.append(s)

        # Create the rendering jobs and add them to the queue.
        for r in render_list:
            job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
            job.sequence = unreal.SoftObjectPath(i["master_sequence"])
            job.map = unreal.SoftObjectPath(i["master_level"])
            job.author = "OpenPype"

            # User data could be used to pass data to the job, that can be
            # read in the job's OnJobFinished callback. We could,
            # for instance, pass the AvalonPublishInstance's path to the job.
            # job.user_data = ""

            settings = job.get_configuration().find_or_add_setting_by_class(
                unreal.MoviePipelineOutputSetting)
            settings.output_resolution = unreal.IntPoint(1920, 1080)
            settings.custom_start_frame = r.get("frame_range")[0]
            settings.custom_end_frame = r.get("frame_range")[1]
            settings.use_custom_playback_range = True
            settings.file_name_format = "{sequence_name}.{frame_number}"
            settings.output_directory.path = f"{render_dir}/{r.get('output')}"

            renderPass = job.get_configuration().find_or_add_setting_by_class(
                unreal.MoviePipelineDeferredPassBase)
            renderPass.disable_multisample_effects = True

            job.get_configuration().find_or_add_setting_by_class(
                unreal.MoviePipelineImageSequenceOutput_PNG)

    # If there are jobs in the queue, start the rendering process.
    if queue.get_jobs():
        global executor
        executor = unreal.MoviePipelinePIEExecutor()
        executor.on_executor_finished_delegate.add_callable_unique(
            _queue_finish_callback)
        executor.on_individual_job_finished_delegate.add_callable_unique(
            _job_finish_callback)  # Only available on PIE Executor
        executor.execute(queue)
